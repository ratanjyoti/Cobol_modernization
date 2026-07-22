import os
import re
from typing import Any

from sqlalchemy.orm import Session

from Agents.implementations.business_logic_extractor import BusinessLogicExtractorAgent
from Agents.infrastructure.chat_client_factory import ChatClientFactory
from Chunking.context.chunk_context_manager import ChunkContextManager
from Persistence.sqlite.models import BusinessRule, ChunkAnalysis, FileChunk, ProjectFile


class LogicExtractionProcess:
    """
    Runs business rule extraction across all completed COBOL chunks in a project run.
    Uses chunk technical YAML + raw COBOL + context packet as evidence.
    """

    LOGIC_RE = re.compile(
        r"\b("
        r"IF|EVALUATE|COMPUTE|ADD|SUBTRACT|MULTIPLY|DIVIDE|"
        r"CALL|EXEC\s+SQL|PERFORM|READ|WRITE|REWRITE|DELETE|"
        r"START|ACCEPT|DISPLAY|OPEN|CLOSE"
        r")\b",
        re.IGNORECASE,
    )

    def __init__(self, db_session: Session, llm_provider: str | dict, api_key: str | None = None):
        self.db = db_session
        self.context_mgr = ChunkContextManager(db_session)

        self.config = (
            llm_provider
            if isinstance(llm_provider, dict)
            else {"mode": llm_provider, "provider": llm_provider, "key": api_key}
        )

        self.llm_provider = (
            self.config.get("mode")
            or self.config.get("provider")
            or "local"
        ).lower()

        self.max_llm_chunks = int(os.getenv("OPENROUTER_MAX_RULE_CHUNKS", "12"))

        try:
            self.llm_client = ChatClientFactory.get_client(self.config)
        except Exception as exc:
            print(f"Cloud/API client unavailable; using local fallback: {exc}")
            self.llm_provider = "local"
            self.llm_client = ChatClientFactory.get_client({"mode": "local", "provider": "local"})

        self.agent = BusinessLogicExtractorAgent(self.llm_client)

    async def extract_all_rules(self, run_id: str) -> int:
        analyses = (
            self.db.query(ChunkAnalysis)
            .filter_by(run_id=run_id, analysis_status="COMPLETED")
            .all()
        )

        analysis_map = {
            analysis.chunk_id: analysis.technical_yaml or ""
            for analysis in analyses
        }

        chunks = (
            self.db.query(FileChunk)
            .filter_by(run_id=run_id)
            .order_by(FileChunk.file_id, FileChunk.chunk_index)
            .all()
        )

        files = {
            file.id: file
            for file in self.db.query(ProjectFile).filter_by(run_id=run_id).all()
        }

        prepared_rules = []
        llm_used_count = 0

        for chunk in chunks:
            project_file = files.get(chunk.file_id)

            if not self._is_legacy_source_chunk(project_file, chunk.content):
                continue

            technical_yaml = analysis_map.get(chunk.id) or self._generate_local_yaml(chunk)

            context_packet = self.context_mgr.build_context_for_chunk(
                run_id,
                chunk.file_id,
                chunk.chunk_index,
            )

            use_llm = (
                self.llm_provider in {"openrouter", "api", "custom", "cloud"}
                and llm_used_count < self.max_llm_chunks
            )

            if use_llm:
                llm_used_count += 1

            result = self.agent.extract_rules(
                technical_yaml=technical_yaml,
                raw_code=chunk.content or "",
                context_packet=context_packet,
                use_llm=use_llm,
                source_name=project_file.filename if project_file else "Unknown",
            )

            prepared_rules.extend(
                self._prepare_agent_result(
                    result=result,
                    chunk=chunk,
                    technical_yaml=technical_yaml,
                )
            )

        self._replace_rules(run_id, prepared_rules)

        return len(prepared_rules)

    def _replace_rules(self, run_id: str, prepared_rules: list[dict]) -> None:
        """
        Safely replaces all rules for a run.
        """
        try:
            self.db.query(BusinessRule).filter_by(run_id=run_id).delete(synchronize_session=False)

            for index, rule in enumerate(prepared_rules, start=1):
                rule_text = rule["rule_text"]
                functional_logic = rule.get("functional_logic") or ""

                self.db.add(BusinessRule(
                    run_id=run_id,
                    chunk_id=rule["chunk_id"],
                    file_id=rule["file_id"],
                    chunk_index=rule["chunk_index"],
                    rule_id=f"BR-{index:03d}",
                    rule_text=rule_text,
                    technical_ref=rule.get("technical_ref") or "",
                    technical_yaml=rule.get("technical_yaml") or "",
                    business_purpose=rule.get("business_purpose") or "",
                    functional_logic=functional_logic,
                    business_logic=functional_logic or rule_text,
                    status="PENDING",
                ))

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

    def _prepare_agent_result(self, result: Any, chunk: FileChunk, technical_yaml: str) -> list[dict]:
        if isinstance(result, dict):
            purpose = result.get("business_purpose", "")
            functional_logic = result.get("functional_logic", "")
            rules = result.get("rules", [])
        elif isinstance(result, list):
            purpose = "Extracted from COBOL source."
            functional_logic = "Refer to technical evidence."
            rules = result
        else:
            purpose = "Extracted from COBOL source."
            functional_logic = "Refer to technical evidence."
            rules = []

        prepared = []

        for rule in rules:
            if isinstance(rule, dict):
                rule_text = (rule.get("rule_text") or rule.get("text") or rule.get("rule") or "").strip()
                technical_ref = (rule.get("technical_ref") or rule.get("source") or rule.get("reference") or "").strip()
                rule_type = (rule.get("rule_type") or "BUSINESS_DECISION").strip()
                confidence = (rule.get("confidence") or "MEDIUM").strip()
            else:
                rule_text = str(rule or "").strip()
                technical_ref = ""
                rule_type = "BUSINESS_DECISION"
                confidence = "MEDIUM"

            if not rule_text:
                continue

            decorated_ref = technical_ref
            if rule_type:
                decorated_ref = f"[{rule_type}] {decorated_ref}".strip()
            if confidence:
                decorated_ref = f"{decorated_ref} | Confidence: {confidence}".strip()

            prepared.append({
                "chunk_id": chunk.id,
                "file_id": chunk.file_id,
                "chunk_index": chunk.chunk_index,
                "business_purpose": purpose,
                "functional_logic": functional_logic,
                "rule_text": rule_text,
                "technical_ref": decorated_ref,
                "technical_yaml": technical_yaml,
            })

        return prepared

    def _is_legacy_source_chunk(self, project_file: ProjectFile | None, content: str | None) -> bool:
        if not project_file:
            return False

        filename = (project_file.filename or "").lower()
        language = (project_file.detected_lang or "").lower()

        is_cobol_file = (
            filename.endswith((".cob", ".cbl", ".cpy", ".jcl"))
            or ".cob." in filename
            or ".cbl." in filename
        )

        is_cobol_language = language.startswith("cobol") or language in {"jcl", "copybook"}

        return (is_cobol_file or is_cobol_language) and self._is_logic_candidate(content)

    def _is_logic_candidate(self, content: str | None) -> bool:
        return bool(content and self.LOGIC_RE.search(content))

    def _generate_local_yaml(self, chunk: FileChunk) -> str:
        blocks = []

        for line_no, raw_line in enumerate((chunk.content or "").splitlines(), start=1):
            line = self._strip_sequence_number(raw_line).strip()

            if not line:
                continue

            if line.upper().startswith(("*", "*>")):
                continue

            if not self.LOGIC_RE.search(line):
                continue

            safe_description = line.replace('"', "'")[:240]

            blocks.append(
                "    - name: \"line-{line_no}\"\n"
                "      type: \"BUSINESS_LOGIC\"\n"
                "      description: \"{description}\"\n"
                "      calls: []".format(
                    line_no=line_no,
                    description=safe_description,
                )
            )

        if not blocks:
            return "control_flow:\n  logic_blocks: []\n"

        return "control_flow:\n  logic_blocks:\n" + "\n".join(blocks) + "\n"

    @staticmethod
    def _strip_sequence_number(line: str) -> str:
        return re.sub(r"^\d{5,6}\s+", "", str(line or "").strip())