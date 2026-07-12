import re
from Persistence.sqlite.models import ConsistencyDiscrepancy, FileChunk


class CodeReconciler:
    @staticmethod
    def stitch(chunks_code: list[str], class_name: str = "MigratedProgram"):
        merged = "\n\n".join(code for code in chunks_code if code)
        merged = CodeReconciler._dedupe_imports(merged)
        merged = CodeReconciler._dedupe_public_class(merged, class_name)
        return merged.strip() + "\n"

    @staticmethod
    def _dedupe_imports(merged: str) -> str:
        imports = re.findall(r"^\s*import\s+[^;]+;", merged, re.MULTILINE)
        unique_imports = sorted({line.strip() for line in imports})
        body = re.sub(r"^\s*import\s+[^;]+;\s*", "", merged, flags=re.MULTILINE)
        return ("\n".join(unique_imports) + "\n\n" if unique_imports else "") + body

    @staticmethod
    def _dedupe_public_class(merged: str, class_name: str) -> str:
        class_matches = list(re.finditer(r"public\s+class\s+([A-Za-z_]\w*)\s*\{", merged))
        if len(class_matches) <= 1:
            return merged

        first_name = class_matches[0].group(1) or class_name
        body = re.sub(r"public\s+class\s+[A-Za-z_]\w*\s*\{", "", merged)
        body = re.sub(r"}\s*$", "", body.strip())
        return f"public class {first_name} {{\n{body}\n}}"

    @staticmethod
    def resolve_forward_references(merged_code, signatures):
        for legacy, target in signatures.items():
            merged_code = merged_code.replace(f"// TODO: Call {legacy}", f"{target};")
            merged_code = merged_code.replace(f"// Pending: {legacy}", f"{target};")
        return merged_code

    @staticmethod
    def quarkus_enrich(code: str, annotations: list[str] | None = None) -> str:
        annotations = annotations or ["@ApplicationScoped", "@Transactional"]
        if "public class" not in code:
            return code
        imports = "import jakarta.enterprise.context.ApplicationScoped;\nimport jakarta.transaction.Transactional;\n"
        for annotation in annotations:
            if annotation not in code:
                code = re.sub(r"(public\s+class\s+)", annotation + "\n" + r"\1", code, count=1)
        return CodeReconciler._dedupe_imports(imports + code)


class AssemblyService:
    def __init__(self, db_session):
        self.db = db_session

    def assemble_file(self, run_id: str, file_id: int, class_name: str = "MigratedProgram", enrich_quarkus: bool = False) -> str:
        chunks = self.db.query(FileChunk).filter_by(
            run_id=run_id,
            file_id=file_id,
        ).order_by(FileChunk.chunk_index.asc()).all()
        code = CodeReconciler.stitch([chunk.converted_code or "" for chunk in chunks], class_name=class_name)
        if enrich_quarkus:
            code = CodeReconciler.quarkus_enrich(code)
        return code

    def migration_report(self, run_id: str, file_id: int | None = None) -> str:
        query = self.db.query(FileChunk).filter(FileChunk.run_id == run_id)
        discrepancy_query = self.db.query(ConsistencyDiscrepancy).filter(ConsistencyDiscrepancy.run_id == run_id)
        if file_id is not None:
            query = query.filter(FileChunk.file_id == file_id)
            discrepancy_query = discrepancy_query.filter(ConsistencyDiscrepancy.file_id == file_id)

        chunks = query.all()
        discrepancies = discrepancy_query.all()
        total_tokens = sum(chunk.tokens_used or 0 for chunk in chunks)
        total_time = sum(chunk.processing_time or 0 for chunk in chunks)
        unresolved = [chunk for chunk in chunks if chunk.status == "FAILED"]

        lines = [
            "# Migration Report",
            "",
            f"Total Tokens Consumed: {total_tokens}",
            f"Processing Time: {total_time:.2f}s",
            "",
            "## Consistency Errors",
        ]
        if discrepancies:
            lines.extend(f"- {d.discrepancy_type}: {d.legacy_name} expected `{d.expected_value}` got `{d.actual_value}`" for d in discrepancies)
        else:
            lines.append("- None")

        lines.extend(["", "## Unresolved Refs / Failed Chunks"])
        if unresolved:
            lines.extend(f"- Chunk {chunk.chunk_index}: {chunk.error_message or 'failed'}" for chunk in unresolved)
        else:
            lines.append("- None")
        return "\n".join(lines) + "\n"
