import os
import zipfile
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from Persistence.sqlite.models import ProjectFile, FileStatus
from Chunking.core.language_detector import LanguageDetector
from source.websockets.socket_manager import manager

class DiscoveryProcess:
    def __init__(self, db_session, upload_dir="data/uploads"):
        self.db = db_session
        self.upload_dir = Path(upload_dir)
        self.detector = LanguageDetector()

    def _save_project_file(self, run_id: str, filename: str, filepath: str, detected_lang: str, size: int = 0):
        """Helper to persist file metadata to the database."""
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
        """Helper to send WebSocket notifications without blocking."""
        await manager.send_notification(run_id, {
            "event": "LANGUAGE_DETECTED",
            "file": filename,
            "suggested_lang": lang,
            "is_valid": is_valid
        })
        # Prevent flooding the browser socket
        await asyncio.sleep(0.05)

    async def process_zip_upload(self, run_id: str, zip_file_path: str) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id
        project_folder.mkdir(parents=True, exist_ok=True)

        # Extract zip in thread to prevent API freeze
        def extract_zip():
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(project_folder)
        
        await asyncio.to_thread(extract_zip)

        mapped_files = []
        for full_path in project_folder.rglob("*"):
            if full_path.is_dir() or full_path.name.startswith('.'):
                continue
            
            rel_path = str(full_path.relative_to(project_folder))
            filename = full_path.name
            lang, is_valid = self.detector.validate_and_detect(str(full_path))
            size = full_path.stat().st_size
            
            file_record = self._save_project_file(run_id, filename, rel_path, lang, size)
            mapped_files.append(file_record)

            # AWAIT is required here because _notify_detection is async
            await self._notify_detection(run_id, filename, lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_folder(self, run_id: str, folder_path: str) -> List[Dict[str, Any]]:
        source_path = Path(folder_path)
        mapped_files = []

        for full_path in source_path.rglob("*"):
            if full_path.is_dir() or full_path.name.startswith("."): 
                continue
                
            rel_path = str(full_path.relative_to(source_path))
            filename = full_path.name
            detected_lang, is_valid = self.detector.validate_and_detect(str(full_path))
            size = full_path.stat().st_size
            
            file_record = self._save_project_file(run_id, filename, rel_path, detected_lang, size)
            mapped_files.append(file_record)
            
            # AWAIT is required here
            await self._notify_detection(run_id, filename, detected_lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_individual_files(self, run_id: str, files) -> List[Dict[str, Any]]:
        project_folder = self.upload_dir / run_id
        project_folder.mkdir(parents=True, exist_ok=True)

        mapped_files = []
        for upload in files:
            filename = Path(upload.filename).name
            destination = project_folder / filename
            
            # AWAIT the read operation
            contents = await upload.read()
            # Write in thread to avoid blocking
            await asyncio.to_thread(destination.write_bytes, contents)

            detected_lang, is_valid = self.detector.validate_and_detect(str(destination))
            file_record = self._save_project_file(run_id, filename, filename, detected_lang, len(contents))
            mapped_files.append(file_record)
            
            # AWAIT is required here
            await self._notify_detection(run_id, filename, detected_lang, is_valid)

        self.db.commit()
        return mapped_files

    async def process_upload(self, run_id: str, zip_path: str):
        # AWAIT is required because process_zip_upload is async
        return await self.process_zip_upload(run_id, zip_path)
