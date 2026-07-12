import re
from sqlalchemy.orm import Session
from Persistence.sqlite.models import ConsistencyDiscrepancy, SignatureRegistry, TypeMappingTable
from Chunking.core.type_mapping_table import infer_target_type, to_camel_case


class ConsistencyEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def clean_to_camel_case(self, legacy_name: str) -> str:
        return to_camel_case(legacy_name)

    def lock_variable(self, run_id: str, legacy_name: str, legacy_type: str, file_id: int | None = None, target_language: str = "java"):
        legacy_key = (legacy_name or "").upper()
        target_name = to_camel_case(legacy_key)
        target_type = infer_target_type(legacy_type, target_language)
        existing = self.db.query(TypeMappingTable).filter_by(
            run_id=run_id,
            file_id=file_id,
            legacy_variable=legacy_key,
        ).first()
        if existing:
            return existing.target_field_name, existing.target_type

        mapping = TypeMappingTable(
            run_id=run_id,
            file_id=file_id,
            legacy_variable=legacy_key,
            legacy_type=(legacy_type or "").upper(),
            target_type=target_type,
            target_field_name=target_name,
        )
        self.db.add(mapping)
        return target_name, target_type

    def lock_signature(self, run_id: str, legacy_name: str, target_method: str | None = None, target_signature: str | None = None, file_id: int | None = None):
        legacy_key = (legacy_name or "").strip().rstrip(".").upper()
        method = target_method or to_camel_case(legacy_key)
        signature = target_signature or f"void {method}()"
        existing = self.db.query(SignatureRegistry).filter_by(
            run_id=run_id,
            file_id=file_id,
            legacy_name=legacy_key,
        ).first()
        if existing:
            return existing

        registry = SignatureRegistry(
            run_id=run_id,
            file_id=file_id,
            legacy_name=legacy_key,
            target_method_name=method,
            target_signature=signature,
        )
        self.db.add(registry)
        return registry

    def validate_signature(self, run_id: str, legacy_name: str, actual_signature: str, file_id: int | None = None, chunk_index: int | None = None):
        legacy_key = (legacy_name or "").strip().rstrip(".").upper()
        existing = self.db.query(SignatureRegistry).filter_by(
            run_id=run_id,
            file_id=file_id,
            legacy_name=legacy_key,
        ).first()
        if not existing:
            method_match = re.search(r"\b([A-Za-z_]\w*)\s*\(", actual_signature or "")
            method_name = method_match.group(1) if method_match else to_camel_case(legacy_key)
            return self.lock_signature(run_id, legacy_key, method_name, actual_signature, file_id)

        if existing.target_signature and actual_signature and existing.target_signature != actual_signature:
            self.db.add(ConsistencyDiscrepancy(
                run_id=run_id,
                file_id=file_id,
                chunk_index=chunk_index,
                discrepancy_type="SIGNATURE_MISMATCH",
                legacy_name=legacy_key,
                expected_value=existing.target_signature,
                actual_value=actual_signature,
                message=f"Signature for {legacy_key} differs from locked registry value.",
            ))
        return existing

    def validate_type_usage(self, run_id: str, legacy_name: str, actual_type: str, file_id: int | None = None, chunk_index: int | None = None):
        legacy_key = (legacy_name or "").upper()
        mapping = self.db.query(TypeMappingTable).filter_by(
            run_id=run_id,
            file_id=file_id,
            legacy_variable=legacy_key,
        ).first()
        if mapping and mapping.target_type and actual_type and mapping.target_type != actual_type:
            self.db.add(ConsistencyDiscrepancy(
                run_id=run_id,
                file_id=file_id,
                chunk_index=chunk_index,
                discrepancy_type="TYPE_MISMATCH",
                legacy_name=legacy_key,
                expected_value=mapping.target_type,
                actual_value=actual_type,
                message=f"Type for {legacy_key} differs from locked mapping value.",
            ))
        return mapping
