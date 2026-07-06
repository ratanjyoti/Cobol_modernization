import os
import zipfile
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set
import stat 
from git import GitCommandError, Repo

# Models and Services
from Persistence.sqlite.models import FileChunk, FileComplexity, ProjectFile, FileStatus, ProjectComplexity
from Chunking.core.language_detector import LanguageDetector
from Chunking.core.complexity_scorer import ComplexityScorer
from Chunking.core.sizing_router import SizingRouter
from Chunking.chunking_orchestrator import ChunkingOrchestrator
from Chunking.dependency_scanner.dependency_manager import DependencyManager 
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

    # --- CORE PIPELINE: Save -> Scan -> Score -> Chunk ---
    async def _save_and_scan(self, run_id: str, full_path: Path, filename: str, rel_path: str, lang: str):
        # 1. Save Basic File Info to DB
        size = full_path.stat().st_size
        project_file = self._save_project_file(run_id, filename, rel_path, lang, size)
        
        # We read the content once and reuse it for all steps
        content = ""
        try:
            content = full_path.read_text(errors='ignore')
        except Exception as e:
            print(f"Could not read file {filename}: {e}")

        # 2. Perform Dependency Scan, Complexity Scoring, and Chunking
        # We wrap these in to_thread because they are CPU-intensive Regex operations
        def process_intelligence():
            # A. Dependency Scan (CALLs, COPYs, SQL)
            dep_manager = DependencyManager(self.db)
            dep_manager.scan_and_store(run_id, filename, content, lang)

            # B. Complexity Scoring
            # Store both per-file scoring details and the highest run-level score.
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
                complexity_record = ProjectComplexity(
                    run_id=run_id,
                    score=comp_data["score"],
                    tier=comp_data["tier"],
                    reasoning_effort=comp_data["reasoning_effort"]
                )
                self.db.add(complexity_record)

            # C. Smart Chunking
            # Only chunks if the SizingRouter says the file is too large
            if SizingRouter.needs_chunking(content):
                self.chunking_orchestrator.process_file(
                    run_id=run_id, 
                    file_id=project_file.id, 
                    filename=filename, 
                    content=content, 
                    lang=lang
                )
            else:
                # Even if not chunked, we store it as a single chunk (Index 0) 
                # so the SLM knows where to look.
                self.chunking_orchestrator.process_file(run_id, project_file.id, filename, content, lang)

        try:
            await asyncio.to_thread(process_intelligence)
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

    async def _notify_detection(self, run_id: str, filename: str, lang: str, is_valid: bool):
        await manager.send_notification(run_id, {
            "event": "LANGUAGE_DETECTED",
            "file": filename,
            "suggested_lang": lang,
            "is_valid": is_valid
        })

    # --- Ingestion Methods ---
    async def ingest_local_git_repo(self, run_id: str, repo_path: str) -> List[Dict[str, Any]]:
        source_path = Path(repo_path).expanduser().resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        if not (source_path / ".git").exists():
            raise ValueError("Not a Git repository (missing .git folder)")

        return await self.process_folder(run_id, str(source_path))

    async def ingest_github_repo(self, run_id: str, repo_url: str, github_token: str = None) -> List[Dict[str, Any]]:
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

            return await self.process_folder(run_id, str(project_folder))
        except Exception:
            self._force_remove_tree(project_folder)
            raise

    async def process_folder_upload(self, run_id: str, files: List[Any], paths: List[str]) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id / "local_repo"
        project_folder.mkdir(parents=True, exist_ok=True)
        mapped_files = []

        for file_obj, rel_path in zip(files, paths):
            rel_path_obj = Path(rel_path)
            if ".git" in rel_path_obj.parts:
                continue
            if rel_path_obj.suffix.lower() not in self.allowed_extensions:
                continue

            destination = project_folder / rel_path_obj
            destination.parent.mkdir(parents=True, exist_ok=True)

            with open(destination, "wb") as buffer:
                while content := await file_obj.read(1024 * 1024):
                    buffer.write(content)

            filename = rel_path_obj.name
            lang, is_valid = await asyncio.to_thread(self.detector.validate_and_detect, str(destination))
            file_record = await self._save_and_scan(run_id, destination, filename, str(rel_path_obj), lang)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            await self._notify_detection(run_id, filename, lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_folder(self, run_id: str, folder_path: str) -> List[Dict[str, Any]]:
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

            file_record = await self._save_and_scan(run_id, full_path, filename, rel_path, lang)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            await self._notify_detection(run_id, filename, lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_zip_upload(self, run_id: str, zip_file_path: str) -> List[Dict[str, Any]]:
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
            
            file_record = await self._save_and_scan(run_id, full_path, filename, rel_path, lang)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)

            await self._notify_detection(run_id, filename, lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_individual_files(self, run_id: str, files) -> List[Dict[str, Any]]:
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
            
            file_record = await self._save_and_scan(run_id, destination, filename, filename, detected_lang)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            
            await self._notify_detection(run_id, filename, detected_lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_upload(self, run_id: str, zip_path: str):
        return await self.process_zip_upload(run_id, zip_path)





