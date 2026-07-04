import os
import zipfile
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set
import stat 
from git import GitCommandError, Repo
from Persistence.sqlite.models import ProjectFile, FileStatus
from Chunking.core.language_detector import LanguageDetector
from source.websockets.socket_manager import manager
# --- ADDED IMPORT ---
from Chunking.dependency_scanner.dependency_manager import DependencyManager 

class DiscoveryProcess:
    def __init__(self, db_session, upload_dir="data/uploads"):
        self.db = db_session
        self.upload_dir = Path(upload_dir)
        self.detector = LanguageDetector()
        
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
        self.db.flush() 
        return {
            "id": str(project_file.id),
            "filename": filename,
            "filepath": filepath,
            "rel_path": filepath,
            "lang": detected_lang,
            "status": FileStatus.PENDING_CONFIRMATION.value,
            "size": size,
            "chunks": 1
        }

    # --- NEW HELPER METHOD: Handles DB save + Dependency Scan ---
    async def _save_and_scan(self, run_id: str, full_path: Path, filename: str, rel_path: str, lang: str):
        # 1. Save to Database
        size = full_path.stat().st_size
        file_record = self._save_project_file(run_id, filename, rel_path, lang, size)
        
        # 2. Perform Dependency Scan
        try:
            # We run this in a thread to avoid blocking the event loop during file I/O
            def scan_file():
                dep_manager = DependencyManager(self.db)
                with open(full_path, 'r', errors='ignore') as f:
                    content = f.read()
                dep_manager.scan_and_store(run_id, filename, content, lang)
            
            await asyncio.to_thread(scan_file)
        except Exception as e:
            print(f"Dependency scan failed for {filename}: {e}")

        return file_record

    async def _notify_detection(self, run_id: str, filename: str, lang: str, is_valid: bool):
        await manager.send_notification(run_id, {
            "event": "LANGUAGE_DETECTED",
            "file": filename,
            "suggested_lang": lang,
            "is_valid": is_valid
        })

    async def ingest_local_git_repo(self, run_id: str, repo_path: str) -> List[Dict[str, Any]]:
        source_path = Path(repo_path).expanduser().resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        if not (source_path / ".git").exists():
            raise ValueError(f"Not a Git repository (missing .git folder)")

        return await self.process_folder(run_id, str(source_path))

    async def ingest_github_repo(self, run_id: str, repo_url: str, github_token: str = None) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id
        if project_folder.exists():
            self._force_remove_tree(project_folder) 
        project_folder.mkdir(parents=True, exist_ok=True)

        try:
            if github_token:
                repo_url = repo_url.replace("https://", f"https://{github_token}@")

            await asyncio.to_thread(Repo.clone_from, repo_url, str(project_folder), depth=1)
            git_dir = project_folder / ".git"
            if git_dir.exists():
                self._force_remove_tree(git_dir)

            return await self.process_folder(run_id, str(project_folder))

        except Exception as e:
            self._force_remove_tree(project_folder)
            raise e

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

            # FIXED: Now calls _save_and_scan
            file_record = await self._save_and_scan(run_id, full_path, filename, rel_path, lang)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            await self._notify_detection(run_id, filename, lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_folder_upload(self, run_id: str, files: List[Any], paths: List[str]):
        project_folder = self.upload_dir / run_id / "local_repo"
        project_folder.mkdir(parents=True, exist_ok=True)

        mapped_files = []

        for file_obj, rel_path in zip(files, paths):
            if ".git" in rel_path: continue
            if Path(rel_path).suffix.lower() not in self.allowed_extensions:
                continue

            destination = project_folder / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            with open(destination, "wb") as buffer:
                while content := await file_obj.read(1024 * 1024):
                    buffer.write(content)
            
            filename = Path(rel_path).name
            lang, is_valid = await asyncio.to_thread(self.detector.validate_and_detect, str(destination))
            
            # FIXED: Now calls _save_and_scan
            file_record = await self._save_and_scan(run_id, destination, filename, rel_path, lang)
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
            
            # FIXED: Now calls _save_and_scan
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
            
            # FIXED: Now calls _save_and_scan
            file_record = await self._save_and_scan(run_id, destination, filename, filename, detected_lang)
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            
            await self._notify_detection(run_id, filename, detected_lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_upload(self, run_id: str, zip_path: str):
        return await self.process_zip_upload(run_id, zip_path)
