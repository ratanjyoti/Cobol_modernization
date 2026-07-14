import os
import re

from sqlalchemy.orm import Session

from Agents.implementations.business_logic_extractor import BusinessLogicExtractorAgent
from Agents.infrastructure.chat_client_factory import ChatClientFactory
from Chunking.context.chunk_context_manager import ChunkContextManager
from Persistence.sqlite.models import BusinessRule, ChunkAnalysis, FileChunk, ProjectFile


class LogicExtractionProcess:
    LOGIC_RE = re.compile(r"\b(IF|EVALUATE|COMPUTE|CALL|EXEC\s+SQL|PERFORM)\b", re.IGNORECASE)

    def __init__(self, db_session: Session, llm_provider: str, api_key: str = None):
        self.db = db_session
        self.context_mgr = ChunkContextManager(db_session)
        self.llm_provider = (llm_provider or "local").lower()
        self.max_llm_chunks = int(os.getenv("OPENROUTER_MAX_RULE_CHUNKS", "12"))
        try:
            self.llm_client = ChatClientFactory.get_client(self.llm_provider, api_key)
        except Exception as exc:
            print(f"Business rule client unavailable; using local fallback: {exc}")
            self.llm_provider = "local"
            self.llm_client = ChatClientFactory.get_client("local")
        self.agent = BusinessLogicExtractorAgent(self.llm_client)

    async def extract_all_rules(self, run_id: str):
        analyses = (
            self.db.query(ChunkAnalysis)
            .filter_by(run_id=run_id, analysis_status="COMPLETED")
            .all()
        )
        analysis_by_chunk_id = {analysis.chunk_id: analysis for analysis in analyses}

        chunks = (
            self.db.query(FileChunk)
            .filter_by(run_id=run_id)
            .order_by(FileChunk.file_id, FileChunk.chunk_index)
            .all()
        )

        prepared_rules = []
        llm_used = 0
        file_by_id = {
            file.id: file
            for file in self.db.query(ProjectFile).filter_by(run_id=run_id).all()
        }

        for chunk in chunks:
            project_file = file_by_id.get(chunk.file_id)
            if not self._is_legacy_source_chunk(project_file, chunk.content):
                continue

            analysis = analysis_by_chunk_id.get(chunk.id)
            technical_yaml = analysis.technical_yaml if analysis else self._local_technical_yaml(chunk)
            context_packet = self.context_mgr.build_context_for_chunk(run_id, chunk.file_id, chunk.chunk_index)
            use_llm = self.llm_provider == "openrouter" and llm_used < self.max_llm_chunks
            if use_llm:
                llm_used += 1

            rules = self.agent.extract_rules(
                technical_yaml=technical_yaml if (analysis or use_llm) else "",
                raw_code=chunk.content,
                context_packet=context_packet,
                use_llm=use_llm,
            )

            for rule in rules:
                rule_text = (rule.get("rule_text") or "").strip()
                if not rule_text:
                    continue
                prepared_rules.append({
                    "chunk_id": chunk.id,
                    "file_id": chunk.file_id,
                    "chunk_index": chunk.chunk_index,
                    "rule_text": rule_text,
                    "technical_ref": (rule.get("technical_ref") or "").strip(),
                    "technical_yaml": technical_yaml,
                })

        self.db.rollback()
        self.db.query(BusinessRule).filter_by(run_id=run_id).delete(synchronize_session=False)
        for index, rule in enumerate(prepared_rules, start=1):
            self.db.add(BusinessRule(
                run_id=run_id,
                chunk_id=rule["chunk_id"],
                file_id=rule["file_id"],
                chunk_index=rule["chunk_index"],
                rule_id=f"BR-{index:03d}",
                rule_text=rule["rule_text"],
                technical_ref=rule["technical_ref"],
                technical_yaml=rule["technical_yaml"],
                business_logic=rule["rule_text"],
                status="PENDING",
            ))

        self.db.commit()
        return len(prepared_rules)

    def _is_legacy_source_chunk(self, project_file: ProjectFile | None, content: str | None) -> bool:
        if not project_file:
            return False
        filename = (project_file.filename or "").lower()
        language = (project_file.detected_lang or "").lower()
        is_cobol_file = filename.endswith((".cob", ".cbl", ".cpy")) or ".cob." in filename
        is_cobol_language = language.startswith("cobol")
        return (is_cobol_file or is_cobol_language) and self._is_logic_candidate(content)
    def _is_logic_candidate(self, content: str | None) -> bool:
        return bool(content and self.LOGIC_RE.search(content))

    def _local_technical_yaml(self, chunk: FileChunk) -> str:
        lines = []
        for line_no, raw_line in enumerate((chunk.content or "").splitlines(), start=1):
            line = raw_line.strip()
            if not line or not self.LOGIC_RE.search(line):
                continue
            safe_description = line.replace('"', "'")[:240]
            lines.append(
                "    - name: \"line-{line_no}\"\n"
                "      type: \"BUSINESS_LOGIC\"\n"
                "      description: \"{description}\"\n"
                "      calls: []".format(line_no=line_no, description=safe_description)
            )
        if not lines:
            return "control_flow:\n  logic_blocks: []\n"
        return "control_flow:\n  logic_blocks:\n" + "\n".join(lines) + "\n"
