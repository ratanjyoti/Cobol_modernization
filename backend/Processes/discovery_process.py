# Implementation for discovery_process.py
import os
import zipfile
from pathlib import Path
from Persistence.sqlite.models import ProjectFile, FileStatus
from Chunking.core.language_detector import LanguageDetector


class DiscoveryProcess:
    def __init__(self, db_session, upload_dir="data/uploads"):
        self.db = db_session
        self.upload_dir = upload_dir
        self.detector = LanguageDetector()

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

    def process_zip_upload(self, run_id: str, zip_file_path: str):
        project_folder = Path(self.upload_dir) / run_id
        project_folder.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(project_folder)

        mapped_files = self.map_files_to_db(run_id, str(project_folder))
        return mapped_files

    def map_files_to_db(self, run_id: str, source_path: str):
        mapped_files = []
        for root, _dirs, files in os.walk(source_path):
            for filename in files:
                if filename.startswith("."):
                    continue

                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, source_path)
                detected_lang, _is_valid = self.detector.validate_and_detect(full_path)
                size = os.path.getsize(full_path)
                mapped_files.append(
                    self._save_project_file(run_id, filename, rel_path, detected_lang, size)
                )

        self.db.commit()
        return mapped_files

    def process_upload(self, run_id: str, zip_path: str):
        return self.process_zip_upload(run_id, zip_path)

    def process_folder(self, run_id: str, folder_path: str):
        return self.map_files_to_db(run_id, folder_path)

    async def process_individual_files(self, run_id: str, files):
        project_folder = Path(self.upload_dir) / run_id
        project_folder.mkdir(parents=True, exist_ok=True)

        mapped_files = []
        for upload in files:
            filename = Path(upload.filename).name
            destination = project_folder / filename
            contents = await upload.read()
            destination.write_bytes(contents)

            detected_lang, _is_valid = self.detector.validate_and_detect(str(destination))
            mapped_files.append(
                self._save_project_file(run_id, filename, filename, detected_lang, len(contents))
            )

        self.db.commit()
        return mapped_files
