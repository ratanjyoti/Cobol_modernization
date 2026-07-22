from pathlib import Path

from sqlalchemy.orm import Session

from Agents.implementations.cobol_analyzer_agent import CobolAnalyzerAgent
from Agents.implementations.technical_analyzer import TechnicalAnalyzerAgent
from Agents.infrastructure.chat_client_factory import ChatClientFactory
from Chunking.context.chunk_context_manager import ChunkContextManager
from Persistence.sqlite.models import ChunkAnalysis, FileChunk, ProjectFile, TechnicalAnalysis
from paths import UPLOADS_DIR


class AnalysisProcess:
    def __init__(self, db_session: Session, llm_provider: str | dict, api_key: str = None):
        self.db = db_session
        self.context_mgr = ChunkContextManager(db_session)

        self.config = (
            llm_provider
            if isinstance(llm_provider, dict)
            else {"mode": llm_provider, "provider": llm_provider, "key": api_key}
        )

        self.llm_client = ChatClientFactory.get_client(self.config)
        self.agent = CobolAnalyzerAgent(self.llm_client)
        self.deep_agent = TechnicalAnalyzerAgent(self.llm_client)

    async def analyze_project(self, run_id: str):
        chunks = (
            self.db.query(FileChunk)
            .filter_by(run_id=run_id)
            .order_by(FileChunk.file_id, FileChunk.chunk_index)
            .all()
        )

        try:
            self.db.query(ChunkAnalysis).filter_by(run_id=run_id).delete(
                synchronize_session=False
            )
            self.db.flush()

            for chunk in chunks:
                context = self.context_mgr.build_context_for_chunk(
                    run_id,
                    chunk.file_id,
                    chunk.chunk_index,
                )

                try:
                    technical_yaml = self.agent.generate_technical_yaml(
                        chunk_content=chunk.content,
                        global_types=context.get("global_types", ""),
                        signatures=context.get("global_signatures", ""),
                        context_summary=context.get("summary_history", ""),
                    )

                    self.db.add(
                        ChunkAnalysis(
                            chunk_id=chunk.id,
                            run_id=run_id,
                            technical_yaml=technical_yaml or "",
                            analysis_status="COMPLETED",
                        )
                    )

                except Exception as exc:
                    print(f"Error analyzing chunk {chunk.chunk_index}: {exc}")

                    self.db.add(
                        ChunkAnalysis(
                            chunk_id=chunk.id,
                            run_id=run_id,
                            technical_yaml="",
                            analysis_status="FAILED",
                        )
                    )

                self.db.commit()

            return True

        except Exception:
            self.db.rollback()
            raise

    async def run_deep_analysis(self, run_id: str):
        files = self.db.query(ProjectFile).filter_by(run_id=run_id).all()

        try:
            self.db.query(TechnicalAnalysis).filter_by(run_id=run_id).delete(
                synchronize_session=False
            )
            self.db.flush()

            for project_file in files:
                path = self._resolve_project_file_path(project_file)

                if not path or not path.exists():
                    continue

                content = path.read_text(errors="ignore")

                try:
                    report = await self.deep_agent.analyze_deep(
                        content,
                        project_file.detected_lang or "unknown",
                    )

                    report_json = (
                        report.model_dump_json()
                        if hasattr(report, "model_dump_json")
                        else str(report)
                    )

                    self.db.add(
                        TechnicalAnalysis(
                            run_id=run_id,
                            file_id=project_file.id,
                            filename=project_file.filename,
                            report_json=report_json,
                        )
                    )

                except Exception as exc:
                    print(f"Error running deep analysis for {project_file.filename}: {exc}")

            self.db.commit()
            return True

        except Exception:
            self.db.rollback()
            raise

    def _resolve_project_file_path(self, project_file: ProjectFile) -> Path | None:
        rel = (project_file.filepath or project_file.filename or "").replace("\\", "/").strip("/")

        if not rel or ".." in rel.split("/"):
            return None

        candidates = [
            UPLOADS_DIR / project_file.run_id / rel,
            UPLOADS_DIR / project_file.run_id / "local_repo" / rel,
            UPLOADS_DIR / project_file.run_id / (project_file.filename or ""),
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        return None