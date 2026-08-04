import os
# Owns business logic extraction process orchestration and persistence. Do not put language-specific prompt text here.
import re
from typing import Any
import json
from sqlalchemy.orm import Session
from Chunking.context.chunk_context_manager import ChunkContextManager
from Persistence.sqlite.models import BusinessRule, ChunkAnalysis, FileChunk, FileRelation, FileStatus, ProjectFile
from paths import UPLOADS_DIR
from Agents.infrastructure.chat_client_factory import ChatClientFactory

from pathlib import Path

from Agents.implementations.agentic_business_logic_extractor import (
    AgenticBusinessLogicExtractor,
    BusinessLogicFileContext,
)

class LogicExtractionProcess:
    """
    Runs agentic business-rule extraction across supported legacy files.

    The process loads chunks and database context, while the LangGraph
    orchestrator selects the correct language prompt, performs technical
    analysis, extracts rules, validates the output and repairs invalid output.
    """

    LOGIC_RE = re.compile(
        r"\b("
        r"IF|EVALUATE|COMPUTE|ADD|SUBTRACT|MULTIPLY|DIVIDE|"
        r"CALL|EXEC\s+SQL|PERFORM|READ|WRITE|REWRITE|DELETE|"
        r"START|ACCEPT|DISPLAY|OPEN|CLOSE"
        r")\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        db_session: Session,
        llm_provider: str | dict,
        api_key: str | None = None,
    ):
        self.db = db_session
        self.context_mgr = ChunkContextManager(db_session)

        self.config = (
            llm_provider
            if isinstance(llm_provider, dict)
            else {
                "mode": llm_provider,
                "provider": llm_provider,
                "key": api_key,
            }
        )

        self.llm_provider = (
            self.config.get("mode")
            or self.config.get("provider")
            or "local"
        ).lower()

        self.max_llm_chunks = int(
            os.getenv("OPENROUTER_MAX_RULE_CHUNKS", "12")
        )

        try:
            self.llm_client = ChatClientFactory.get_client(
                self.config
            )
        except Exception as exc:
            print(
                "Cloud/API client unavailable; "
                f"using local fallback: {exc}"
            )

            self.llm_provider = "local"

            self.llm_client = ChatClientFactory.get_client(
                {
                    "mode": "local",
                    "provider": "local",
                }
            )

    async def extract_all_rules(self, run_id: str, force: bool = False) -> dict:
        from Persistence.sqlite.models import Project, ProjectFile

        project = self.db.query(Project).filter_by(run_id=run_id).first()

        if not project:
            raise ValueError(f"Project not found for run_id={run_id}")

        extractor = self._build_agentic_extractor(project)

        files = [
            project_file
            for project_file in self.db.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()
            if self._is_detected_or_confirmed(project_file)
        ]

        total = len(files)
        completed = 0
        cached = 0
        failed = 0
        results = []

        for project_file in files:
            try:
                existing_rules_count = (
                    self.db.query(BusinessRule)
                    .filter(
                        BusinessRule.run_id == run_id,
                        BusinessRule.file_id == project_file.id,
                    )
                    .count()
                )

                if existing_rules_count and not force:
                    cached += 1
                    results.append(
                        {
                            "file_id": project_file.id,
                            "file_name": project_file.filename,
                            "detected_language": (
                                getattr(project_file, "detected_language", None)
                                or getattr(project_file, "detected_lang", None)
                                or ""
                            ),
                            "business_rules_count": existing_rules_count,
                            "status": "cached",
                        }
                    )
                    continue

                if existing_rules_count and force:
                    (
                        self.db.query(BusinessRule)
                        .filter(
                            BusinessRule.run_id == run_id,
                            BusinessRule.file_id == project_file.id,
                        )
                        .delete(synchronize_session=False)
                    )
                    self.db.commit()

                source_code = self._load_source_code_for_file(project_file)
                technical_yaml = self._load_technical_yaml_for_file(
                    run_id=run_id,
                    file_id=project_file.id,
                )
                if not technical_yaml.strip():
                    technical_yaml = self._generate_local_yaml_from_source(source_code)

                if not self._is_legacy_source_chunk(project_file, source_code):
                    results.append(
                        {
                            "file_id": project_file.id,
                            "file_name": project_file.filename,
                            "detected_language": project_file.detected_lang or "",
                            "status": "skipped",
                            "reason": "unsupported_or_empty_source",
                        }
                    )
                    continue

                dependency_context = self._build_dependency_context_for_file(
                    run_id=run_id,
                    file_id=project_file.id,
                )

                glossary_context = self._build_glossary_context(run_id)

                context = self._build_business_file_context(
                    project_file=project_file,
                    technical_yaml=technical_yaml,
                    source_code=source_code,
                    dependency_context=dependency_context,
                    glossary_context=glossary_context,
                )

                result = extractor.extract(context)

                self._persist_agentic_business_logic_result(
                    run_id=run_id,
                    project_file=project_file,
                    result=result,
                )

                completed += 1
                results.append(
                    {
                        "file_id": project_file.id,
                        "file_name": context.file_name,
                        "detected_language": context.detected_language,
                        "agent_name": result.get("agent_name"),
                        "agent_key": result.get("agent_key"),
                        "fallback_used": result.get("fallback_used", False),
                        "fallback_reason": result.get("fallback_reason", ""),
                        "business_rules_count": len(result.get("business_rules") or []),
                        "status": "completed",
                    }
                )

            except Exception as exc:
                failed += 1
                results.append(
                    {
                        "file_id": getattr(project_file, "id", None),
                        "file_name": getattr(project_file, "filename", ""),
                        "detected_language": getattr(project_file, "detected_language", ""),
                        "status": "failed",
                        "error": str(exc),
                    }
                )

        summary = {
            "run_id": run_id,
            "total_files": total,
            "completed_files": completed,
            "cached_files": cached,
            "failed_files": failed,
            "results": results,
        }
        self._write_extraction_summary(run_id, summary)
        return summary

    def extraction_summary(self, run_id: str) -> dict[str, Any]:
        path = self._summary_path(run_id)
        if not path.exists():
            return {"run_id": run_id, "results": []}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return {"run_id": run_id, "results": []}

    def _write_extraction_summary(self, run_id: str, payload: dict[str, Any]) -> None:
        path = self._summary_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _summary_path(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "business_logic" / run_id / "summary.json"

    def _persist_agentic_business_logic_result(
        self,
        run_id: str,
        project_file,
        result: dict,
    ) -> None:
        """
        Store normalized business rules in your existing BusinessRule table.

        Adjust field names if your BusinessRule model uses different columns.
        """

        from Persistence.sqlite.models import BusinessRule

        file_id = getattr(project_file, "id", None)

        rules = result.get("business_rules") or []

        # Store purpose as a rule also, so existing UI can show something immediately.
        business_purpose = result.get("business_purpose") or ""
        functional_logic = self._format_functional_logic(
            result.get("functional_logic") or []
        )
        technical_yaml = result.get("technical_yaml") or ""

        if business_purpose.strip():
            purpose_rule = BusinessRule(
                run_id=run_id,
                file_id=file_id,
                rule_id=f"PURPOSE-{file_id}",
                rule_text=business_purpose,
                business_purpose=business_purpose,
                functional_logic=functional_logic,
                business_logic=functional_logic or business_purpose,
                technical_ref=result.get("file_name", ""),
                technical_yaml=technical_yaml,
                status="PENDING",
            )
            self.db.add(purpose_rule)

        for index, item in enumerate(rules, start=1):
            if not isinstance(item, dict):
                continue

            rule_text = (
                item.get("rule_text")
                or item.get("description")
                or item.get("business_meaning")
                or ""
            )

            if not str(rule_text).strip():
                continue

            rule = BusinessRule(
                run_id=run_id,
                file_id=file_id,
                rule_id=f"BR-{file_id}-{index}",
                rule_text=str(rule_text).strip(),
                technical_ref=str(
                    item.get("technical_reference")
                    or item.get("technical_ref")
                    or ""
                ),
                technical_yaml=technical_yaml,
                business_purpose=business_purpose,
                functional_logic=functional_logic,
                business_logic=str(rule_text).strip(),
                status="PENDING",
            )

            self.db.add(rule)

        self.db.commit()

    def _build_business_file_context(
        self,
        project_file,
        technical_yaml: str,
        source_code: str,
        dependency_context: str = "",
        glossary_context: str = "",
    ) -> BusinessLogicFileContext:
        detected_language = (
            getattr(project_file, "detected_language", None)
            or getattr(project_file, "detected_lang", None)
            or getattr(project_file, "language", None)
            or "unknown"
        )

        file_name = (
            getattr(project_file, "filename", None)
            or getattr(project_file, "file_name", None)
            or getattr(project_file, "relative_path", None)
            or f"file_{getattr(project_file, 'id', '')}"
        )

        return BusinessLogicFileContext(
            file_id=getattr(project_file, "id", ""),
            file_name=file_name,
            detected_language=detected_language,
            source_code=source_code or "",
            technical_yaml=technical_yaml or "",
            dependency_context=dependency_context or "",
            glossary_context=glossary_context or "",
        )

    def _build_agentic_extractor(self, project) -> AgenticBusinessLogicExtractor:
        """Build LLM config from project settings.
        
                    This keeps the business logic orchestrator independent from DB/project models."""

        llm_config = {
            "mode": getattr(project, "ai_mode", None)
            or getattr(project, "llm_provider", None)
            or self.config.get("mode")
            or self.config.get("provider")
            or "local",
            "provider": getattr(project, "llm_provider", None)
            or getattr(project, "ai_mode", None)
            or self.config.get("provider")
            or self.config.get("mode")
            or "local",
            "model": getattr(project, "llm_model", None)
            or getattr(project, "model", None)
            or self.config.get("model")
            or "llama3",
            "url": getattr(project, "custom_api_base_url", None)
            or getattr(project, "api_base_url", None)
            or self.config.get("url")
            or self.config.get("base_url")
            or "http://127.0.0.1:11434",
            "key": getattr(project, "custom_api_key", None)
            or getattr(project, "api_key", None)
            or self.config.get("key")
            or self.config.get("api_key")
            or None,
            "timeout": self.config.get("timeout")
            or os.getenv("BUSINESS_LOGIC_LLM_TIMEOUT", "30"),
            "max_tokens": self.config.get("max_tokens") or 1600,
        }

        return AgenticBusinessLogicExtractor(llm_config=llm_config)

    def _load_source_code_for_file(self, project_file) -> str:
        content = self._read_project_file(project_file)
        if content:
            return content

        for attr_name in ("file_path", "path", "storage_path", "absolute_path"):
            item = getattr(project_file, attr_name, None)
            if not item:
                continue

            try:
                path = Path(item)
                if path.exists() and path.is_file():
                    return path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

        return str(getattr(project_file, "content", "") or "")

    def _load_technical_yaml_for_file(self, run_id: str, file_id: int) -> str:
        rows = (
            self.db.query(ChunkAnalysis, FileChunk)
            .join(FileChunk, ChunkAnalysis.chunk_id == FileChunk.id)
            .filter(
                ChunkAnalysis.run_id == run_id,
                FileChunk.file_id == file_id,
            )
            .order_by(FileChunk.chunk_index)
            .all()
        )

        yaml_parts = []
        for analysis, chunk in rows:
            technical_yaml = getattr(analysis, "technical_yaml", "") or ""
            if technical_yaml.strip():
                yaml_parts.append(
                    f"# chunk_id: {chunk.id}, chunk_index: {chunk.chunk_index}\n"
                    f"{technical_yaml}"
                )

        return "\n\n---\n\n".join(yaml_parts)

    def _build_dependency_context_for_file(self, run_id: str, file_id: int) -> str:
        project_file = self.db.query(ProjectFile).filter_by(id=file_id).first()
        if not project_file:
            return ""

        source_names = {
            item
            for item in (
                project_file.filename,
                project_file.filepath,
                (project_file.filepath or "").replace("\\", "/"),
            )
            if item
        }

        rows = (
            self.db.query(FileRelation)
            .filter(
                FileRelation.run_id == run_id,
                FileRelation.source_file.in_(source_names),
            )
            .limit(100)
            .all()
        )

        items = [
            {
                "source_file": row.source_file,
                "relation_type": row.relation_type,
                "target": row.target_item,
            }
            for row in rows
        ]

        return json.dumps(items, indent=2)

    def _build_glossary_context(self, run_id: str) -> str:
        return ""

    def _format_functional_logic(self, items: Any) -> str:
        if isinstance(items, str):
            return items.strip()

        if not isinstance(items, list):
            return ""

        parts = []
        for item in items:
            if isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                description = str(item.get("description") or "").strip()
                text = f"{title}: {description}".strip(": ").strip()
            else:
                text = str(item or "").strip()

            if text:
                parts.append(text)

        return "\n".join(parts)

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

    def _load_or_create_chunks(self, run_id: str) -> list[FileChunk]:
        chunks = (
            self.db.query(FileChunk)
            .filter_by(run_id=run_id)
            .order_by(FileChunk.file_id, FileChunk.chunk_index)
            .all()
        )
        if chunks:
            return chunks

        project_files = self.db.query(ProjectFile).filter_by(run_id=run_id).all()
        created = []

        for project_file in project_files:
            content = self._read_project_file(project_file)
            if not content or not self._is_legacy_source_chunk(project_file, content):
                continue

            chunk = FileChunk(
                run_id=run_id,
                file_id=project_file.id,
                chunk_index=0,
                content=content,
                start_line=1,
                end_line=content.count("\n") + (1 if content else 0),
                overlap_content="",
                semantic_units='["file:FILE"]',
                status="PENDING",
            )
            self.db.add(chunk)
            created.append(chunk)

        if created:
            self.db.commit()
            return (
                self.db.query(FileChunk)
                .filter_by(run_id=run_id)
                .order_by(FileChunk.file_id, FileChunk.chunk_index)
                .all()
            )

        return []

    def _read_project_file(self, project_file: ProjectFile) -> str:
        rel = (project_file.filepath or project_file.filename or "").replace("\\", "/").strip("/")
        if not rel or ".." in rel.split("/"):
            return ""

        candidates = [
            UPLOADS_DIR / project_file.run_id / rel,
            UPLOADS_DIR / project_file.run_id / "local_repo" / rel,
            UPLOADS_DIR / project_file.run_id / (project_file.filename or ""),
        ]

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate.read_text(errors="ignore")
            except OSError as exc:
                print(f"Could not read uploaded file {candidate}: {exc}")

        return ""

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

    def _is_legacy_source_chunk(
        self,
        project_file: ProjectFile | None,
        content: str | None,
    ) -> bool:
        if not project_file:
            return False

        filename = (
            project_file.filepath
            or project_file.filename
            or ""
        ).lower()

        language = (
            project_file.detected_lang
            or ""
        ).lower()

        supported_extensions = (
            ".cob",
            ".cbl",
            ".cpy",
            ".jcl",
            ".job",
            ".telon",
            ".tps",
            ".pli",
            ".pl1",
            ".sql",
            ".ddl",
        )

        supported_languages = {
            "cobol",
            "copybook",
            "jcl",
            "telon",
            "pli",
            "pl/i",
            "pl1",
            "sql",
            "db2",
        }

        has_supported_extension = filename.endswith(
            supported_extensions
        )

        has_supported_language = (
            language in supported_languages
            or language.startswith("cobol")
            or language.startswith("telon")
        )

        return (
            has_supported_extension
            or has_supported_language
        ) and bool(content and content.strip())

    @staticmethod
    def _is_detected_or_confirmed(project_file: ProjectFile | None) -> bool:
        if not project_file:
            return False
        if project_file.status == FileStatus.CONFIRMED:
            return True
        detected = str(project_file.detected_lang or "").strip().lower()
        return bool(detected and detected != "unknown")

    def _generate_local_yaml_from_source(self, source_code: str | None) -> str:
        class _SourceChunk:
            content = source_code or ""

        return self._generate_local_yaml(_SourceChunk())

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
