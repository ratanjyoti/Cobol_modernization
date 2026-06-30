import os
import zipfile
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set

from Persistence.sqlite.models import ProjectFile, FileStatus
from Chunking.core.language_detector import LanguageDetector
from source.websockets.socket_manager import manager

class DiscoveryProcess:
    def __init__(self, db_session, upload_dir="data/uploads"):
        self.db = db_session
        self.upload_dir = Path(upload_dir)
        self.detector = LanguageDetector()
        
        # Keep only source-code extensions requested for repository ingestion.
        self.allowed_extensions: Set[str] = {
            ".cbl", ".cob", ".cpy",
            ".jcl",
            ".tln", ".tel",
            ".txt",
        }

    def _is_supported_file(self, file_path: Path) -> bool:
        """Checks if the file has an extension we care about."""
        if file_path.is_dir():
            return False
        if file_path.name.startswith('.'): # Ignore hidden files like .git
            return False
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
        }

    async def _notify_detection(self, run_id: str, filename: str, lang: str, is_valid: bool):
        await manager.send_notification(run_id, {
            "event": "LANGUAGE_DETECTED",
            "file": filename,
            "suggested_lang": lang,
            "is_valid": is_valid
        })

    async def process_zip_upload(self, run_id: str, zip_file_path: str) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id
        project_folder.mkdir(parents=True, exist_ok=True)

        def extract_zip():
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(project_folder)
        
        await asyncio.to_thread(extract_zip)

        mapped_files = []
        # Filtered iteration: only process files that match allowed extensions
        for full_path in project_folder.rglob("*"):
            if not self._is_supported_file(full_path):
                continue
            
            rel_path = str(full_path.relative_to(project_folder))
            filename = full_path.name
            lang, is_valid = self.detector.validate_and_detect(str(full_path))
            size = full_path.stat().st_size
            
            file_record = self._save_project_file(run_id, filename, rel_path, lang, size)
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

        all_files = [f for f in source_path.rglob("*") if self._is_supported_file(f)]

        for full_path in all_files:
            rel_path = full_path.relative_to(source_path)
            destination = project_folder / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, full_path, destination)

            rel_path_str = str(rel_path)
            filename = full_path.name
            lang, is_valid = await asyncio.to_thread(self.detector.validate_and_detect, str(destination))
            size = destination.stat().st_size

            file_record = self._save_project_file(run_id, filename, rel_path_str, lang, size)
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
            
            # Check extension before saving to disk
            if not self._is_supported_file(Path(filename)):
                continue

            destination = project_folder / filename
            contents = await upload.read()
            await asyncio.to_thread(destination.write_bytes, contents)

            detected_lang, is_valid = self.detector.validate_and_detect(str(destination))
            file_record = self._save_project_file(run_id, filename, filename, detected_lang, len(contents))
            file_record["is_valid"] = is_valid
            mapped_files.append(file_record)
            
            await self._notify_detection(run_id, filename, detected_lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_upload(self, run_id: str, zip_path: str):
        return await self.process_zip_upload(run_id, zip_path)
