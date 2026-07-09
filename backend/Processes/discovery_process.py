import os
import zipfile
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set
import stat 
from git import GitCommandError, Repo

# Models and Services
from Persistence.sqlite.models import FileChunk, FileComplexity, FileRelation, ProjectFile, FileStatus, ProjectComplexity
from Chunking.core.language_detector import LanguageDetector
from Chunking.core.complexity_scorer import ComplexityScorer
from Chunking.core.sizing_router import SizingRouter
from Chunking.chunking_orchestrator import ChunkingOrchestrator
from Chunking.dependency_scanner.dependency_manager import DependencyManager
from Chunking.dependency_scanner.resolution_service import ResolutionService
from Processes.graphing_process import GraphingProcess
from paths import UPLOADS_DIR
from source.websockets.socket_manager import manager

class DiscoveryProcess:
    def __init__(self, db_session, upload_dir=None):
        self.db = db_session
        self.upload_dir = Path(upload_dir) if upload_dir else UPLOADS_DIR
        self.detector = LanguageDetector()
        
        # Initialize the "Intelligence" tools
        self.scorer = ComplexityScorer()
        self.chunking_orchestrator = ChunkingOrchestrator(self.db)
        
        self.allowed_extensions: Set[str] = {
            ".cbl", ".cob", ".cpy",
            ".jcl", ".sql",
            ".tln", ".tel",
            ".vb", ".bas", ".frm", ".cls",
            ".cs", ".sln", ".csproj", ".vbproj",
            ".xml", ".config",
            ".txt",
        }

    def _force_remove_tree(self, path: Path):
        def handle_remove_readonly(func, path, excinfo):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        if path.exists():
            shutil.rmtree(path, onerror=handle_remove_readonly)

    def _is_supported_file(self, file_path: Path) -> bool:
        if file_path.is_dir(): return False
        if ".git" in file_path.parts: return False
        if file_path.name.startswith('.'): return False
        return file_path.suffix.lower() in self.allowed_extensions

    def _safe_relative_upload_path(self, rel_path: str) -> Path | None:
        normalized = rel_path.replace("\\", "/").strip("/")
        parts = [part for part in normalized.split("/") if part]

        if not parts:
            return None
        if any(part in {".", ".."} for part in parts):
            return None
        if any(":" in part for part in parts):
            return None

        safe_path = Path(*parts)
        if safe_path.is_absolute():
            return None

        return safe_path

    def _save_project_file(self, run_id: str, filename: str, filepath: str, detected_lang: str, size: int = 0):
        project_file = ProjectFile(
            run_id=run_id,
            filename=filename,
            filepath=filepath,
            detected_lang=detected_lang,
            status=FileStatus.PENDING_CONFIRMATION,
        )
        self.db.add(project_file)
        self.db.flush() # Ensures project_file.id is generated
        return project_file

    def _run_file_intelligence(self, run_id: str, project_file: ProjectFile, content: str):
        filename = project_file.filename
        rel_path = project_file.filepath or filename
        lang = project_file.detected_lang or "unknown"

        # A. Dependency Scan (CALLs, COPYs, SQL)
        dep_manager = DependencyManager(self.db)
        dep_manager.scan_and_store(run_id, rel_path, content, lang)

        # B. Complexity Scoring
        comp_data = self.scorer.calculate_score(content)
        existing_file_complexity = self.db.query(FileComplexity).filter(
            FileComplexity.run_id == run_id,
            FileComplexity.file_id == project_file.id,
        ).first()
        file_complexity_values = {
            "filename": filename,
            "filepath": rel_path,
            "score": comp_data["score"],
            "tier": comp_data["tier"],
            "effort": comp_data["reasoning_effort"],
            "logic_count": comp_data["logic_count"],
            "table_count": comp_data["table_count"],
            "table_bonus": comp_data["table_bonus"],
            "if_count": comp_data["if_count"],
            "perform_until_count": comp_data["perform_until_count"],
            "perform_varying_count": comp_data["perform_varying_count"],
            "evaluate_count": comp_data["evaluate_count"],
        }
        if existing_file_complexity:
            for key, value in file_complexity_values.items():
                setattr(existing_file_complexity, key, value)
        else:
            self.db.add(FileComplexity(
                run_id=run_id,
                file_id=project_file.id,
                **file_complexity_values,
            ))

        existing_complexity = self.db.query(ProjectComplexity).filter(
            ProjectComplexity.run_id == run_id
        ).first()
        if existing_complexity:
            if comp_data["score"] > (existing_complexity.score or 0):
                existing_complexity.score = comp_data["score"]
                existing_complexity.tier = comp_data["tier"]
                existing_complexity.reasoning_effort = comp_data["reasoning_effort"]
        else:
            self.db.add(ProjectComplexity(
                run_id=run_id,
                score=comp_data["score"],
                tier=comp_data["tier"],
                reasoning_effort=comp_data["reasoning_effort"],
            ))

        # C. Smart Chunking
        self.chunking_orchestrator.process_file(
            run_id=run_id,
            file_id=project_file.id,
            filename=filename,
            content=content,
            lang=lang,
        )

    def _uploaded_file_candidates(self, project_file: ProjectFile) -> List[Path]:
        rel_path = self._safe_relative_upload_path(project_file.filepath or project_file.filename)
        project_folder = self.upload_dir / project_file.run_id
        candidates = []

        if rel_path is not None:
            candidates.append(project_folder / rel_path)
            candidates.append(project_folder / "local_repo" / rel_path)

        candidates.append(project_folder / project_file.filename)
        return candidates

    def _read_uploaded_file_content(self, project_file: ProjectFile) -> str:
        for candidate in self._uploaded_file_candidates(project_file):
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate.read_text(errors="ignore")
            except OSError as exc:
                print(f"Could not read file {candidate}: {exc}")
        print(f"Uploaded file not found for analysis: {project_file.filepath or project_file.filename}")
        return ""

    def analyze_run(self, run_id: str, file_ids: List[int] | None = None):
        query = self.db.query(ProjectFile).filter(ProjectFile.run_id == run_id)
        if file_ids:
            query = query.filter(ProjectFile.id.in_(file_ids))
        project_files = query.order_by(ProjectFile.id.asc()).all()
        if not project_files:
            return {"files_analyzed": 0}

        target_ids = [project_file.id for project_file in project_files]
        target_paths = [project_file.filepath or project_file.filename for project_file in project_files]
        target_names = [project_file.filename for project_file in project_files]

        self.db.query(FileChunk).filter(
            FileChunk.run_id == run_id,
            FileChunk.file_id.in_(target_ids),
        ).delete(synchronize_session=False)
        self.db.query(FileComplexity).filter(
            FileComplexity.run_id == run_id,
            FileComplexity.file_id.in_(target_ids),
        ).delete(synchronize_session=False)
        self.db.query(FileRelation).filter(
            FileRelation.run_id == run_id,
            FileRelation.source_file.in_(target_paths + target_names),
        ).delete(synchronize_session=False)
        self.db.query(ProjectComplexity).filter(ProjectComplexity.run_id == run_id).delete(synchronize_session=False)
        self.db.flush()

        for project_file in project_files:
            content = self._read_uploaded_file_content(project_file)
            self._run_file_intelligence(run_id, project_file, content)

        self._resolve_dependencies(run_id)
        self.db.commit()
        self._sync_neo4j_graph(run_id)
        return {"files_analyzed": len(project_files)}

    # --- CORE PIPELINE: Save -> Scan -> Score -> Chunk ---
    async def _save_and_scan(self, run_id: str, full_path: Path, filename: str, rel_path: str, lang: str, analyze_inline: bool = True):
        # 1. Save Basic File Info to DB
        size = full_path.stat().st_size
        project_file = self._save_project_file(run_id, filename, rel_path, lang, size)
        
        # We read the content once and reuse it for all steps
        content = ""
        try:
            content = full_path.read_text(errors='ignore')
        except Exception as e:
            print(f"Could not read file {filename}: {e}")

        if analyze_inline:
            try:
                await asyncio.to_thread(self._run_file_intelligence, run_id, project_file, content)
            except Exception as e:
                print(f"Intelligence processing failed for {filename}: {e}")

        chunk_count = self.db.query(FileChunk).filter(
            FileChunk.run_id == run_id,
            FileChunk.file_id == project_file.id,
        ).count()

        # Return the record for the frontend
        return {
            "id": str(project_file.id),
            "filename": filename,
            "filepath": rel_path,
            "rel_path": rel_path,
            "lang": lang,
            "status": FileStatus.PENDING_CONFIRMATION.value,
            "size": size,
            "chunks": chunk_count or 1
        }


    def _resolve_dependencies(self, run_id: str):
        ResolutionService(self.db).resolve_run_relations(run_id)

    def _sync_neo4j_graph(self, run_id: str):
        try:
            GraphingProcess(self.db).build_full_graph(run_id)
        except Exception as e:
            print(f"Neo4j graph sync skipped for {run_id}: {e}")

    async def _notify_detection(self, run_id: str, filename: str, lang: str, is_valid: bool):
        await manager.send_notification(run_id, {
            "event": "LANGUAGE_DETECTED",
            "file": filename,
            "suggested_lang": lang,
            "is_valid": is_valid
        })

    # --- Ingestion Methods ---
    async def ingest_local_git_repo(self, run_id: str, repo_path: str, analyze_inline: bool = True) -> List[Dict[str, Any]]:
        source_path = Path(repo_path).expanduser().resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        if not (source_path / ".git").exists():
            raise ValueError("Not a Git repository (missing .git folder)")

        return await self.process_folder(run_id, str(source_path), analyze_inline)

    async def ingest_github_repo(self, run_id: str, repo_url: str, github_token: str = None, analyze_inline: bool = True) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id
        if project_folder.exists():
            self._force_remove_tree(project_folder)
        project_folder.mkdir(parents=True, exist_ok=True)

        clone_url = repo_url
        if github_token:
            clone_url = repo_url.replace("https://", f"https://{github_token}@", 1)

        try:
            await asyncio.to_thread(Repo.clone_from, clone_url, str(project_folder), depth=1)
            git_dir = project_folder / ".git"
            if git_dir.exists():
                self._force_remove_tree(git_dir)

            return await self.process_folder(run_id, str(project_folder), analyze_inline)
        except Exception:
            self._force_remove_tree(project_folder)
            raise

    async def process_folder_upload(self, run_id: str, files: List[Any], paths: List[str], analyze_inline: bool = True) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id / "local_repo"
        project_folder.mkdir(parents=True, exist_ok=True)
        mapped_files = []

        for file_obj, rel_path in zip(files, paths):
            rel_path_obj = self._safe_relative_upload_path(rel_path)
            if rel_path_obj is None:
                continue
            if ".git" in rel_path_obj.parts:
                continue
            if rel_path_obj.suffix.lower() not in self.allowed_extensions:
                continue

            destination = project_folder / rel_path_obj
            if project_folder.resolve() not in destination.resolve().parents:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)

            with open(destination, "wb") as buffer:
                while content := await file_obj.read(1024 * 1024):
                    buffer.write(content)

            filename = rel_path_obj.name
            lang, is_valid = await asyncio.to_thread(self.detector.validate_and_detect, str(destination))
            file_record = await self._save_and_scan(run_id, destination, filename, str(rel_path_obj), lang, analyze_inline)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            await self._notify_detection(run_id, filename, lang, is_valid)

        self.db.commit()
        if analyze_inline:
            self._resolve_dependencies(run_id)
            self.db.commit()
            self._sync_neo4j_graph(run_id)
        return mapped_files

    async def process_folder(self, run_id: str, folder_path: str, analyze_inline: bool = True) -> List[Dict[str, Any]]:
        source_path = Path(folder_path)
        project_folder = self.upload_dir / run_id
        project_folder.mkdir(parents=True, exist_ok=True)
        mapped_files = []

        all_files = sorted(
            (f for f in source_path.rglob("*") if self._is_supported_file(f)),
            key=lambda path: str(path.relative_to(source_path)).lower()
        )

        for full_path in all_files:
            rel_path = str(full_path.relative_to(source_path))
            filename = full_path.name
            lang, is_valid = await asyncio.to_thread(self.detector.validate_and_detect, str(full_path))

            file_record = await self._save_and_scan(run_id, full_path, filename, rel_path, lang, analyze_inline)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            await self._notify_detection(run_id, filename, lang, is_valid)

        self.db.commit()
        if analyze_inline:
            self._resolve_dependencies(run_id)
            self.db.commit()
            self._sync_neo4j_graph(run_id)
        return mapped_files

    async def process_zip_upload(self, run_id: str, zip_file_path: str, analyze_inline: bool = True) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id
        project_folder.mkdir(parents=True, exist_ok=True)

        def extract_zip():
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(project_folder)
        
        await asyncio.to_thread(extract_zip)

        mapped_files = []
        for full_path in project_folder.rglob("*"):
            if not self._is_supported_file(full_path):
                continue
            
            rel_path = str(full_path.relative_to(project_folder))
            filename = full_path.name
            lang, is_valid = await asyncio.to_thread(self.detector.validate_and_detect, str(full_path))
            
            file_record = await self._save_and_scan(run_id, full_path, filename, rel_path, lang, analyze_inline)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)

            await self._notify_detection(run_id, filename, lang, is_valid)

        self.db.commit()
        if analyze_inline:
            self._resolve_dependencies(run_id)
            self.db.commit()
            self._sync_neo4j_graph(run_id)
        return mapped_files

    async def process_individual_files(self, run_id: str, files, analyze_inline: bool = True) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id
        project_folder.mkdir(parents=True, exist_ok=True)

        mapped_files = []
        for upload in files:
            filename = Path(upload.filename).name
            if not self._is_supported_file(Path(filename)):
                continue

            destination = project_folder / filename
            contents = await upload.read()
            await asyncio.to_thread(destination.write_bytes, contents)

            detected_lang, is_valid = await asyncio.to_thread(self.detector.validate_and_detect, str(destination))
            
            file_record = await self._save_and_scan(run_id, destination, filename, filename, detected_lang, analyze_inline)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            
            await self._notify_detection(run_id, filename, detected_lang, is_valid)

        self.db.commit()
        if analyze_inline:
            self._resolve_dependencies(run_id)
            self.db.commit()
            self._sync_neo4j_graph(run_id)
        return mapped_files

    async def process_upload(self, run_id: str, zip_path: str, analyze_inline: bool = True):
        return await self.process_zip_upload(run_id, zip_path, analyze_inline)










