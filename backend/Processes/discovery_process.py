# Implementation for discovery_process.py
import os
import zipfile
import shutil
from pathlib import Path
from Persistence.sqlite.models import ProjectFile, FileStatus
from Chunking.adapters.lang_detector import LanguageDetector

class DiscoveryProcess:
    def __init__(self, db_session, upload_dir="data/uploads"):
        self.db = db_session
        self.upload_dir = upload_dir

    def map_files_to_db(self, run_id: str, source_path: str):
        mapped_files = []
        for root, dirs, files in os.walk(source_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_path)
                
                # Use the LanguageDetector we built in the previous step
                from Chunking.core.language_detector import LanguageDetector
                detector = LanguageDetector()
                lang, is_valid = detector.validate_and_detect(full_path)
                
                project_file = ProjectFile(
                    run_id=run_id,
                    filename=file,
                    filepath=rel_path,
                    detected_lang=lang,
                    status=FileStatus.PENDING_CONFIRMATION
                )
                self.db.add(project_file)
                mapped_files.append({"file": file, "lang": lang})
        
        self.db.commit()
        return mapped_files
    
    def process_upload(self, run_id: str, zip_path: str):
        # 1. Unzip files to a project-specific folder
        project_folder = Path(f"{self.upload_dir}/{run_id}")
        project_folder.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(project_folder)

        # 2. Walk through the extracted directory
        mapped_files = []
        for root, dirs, files in os.walk(project_folder):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_folder)
                
                # Detect Language
                lang = LanguageDetector.detect(full_path)
                
                # Create Database Entry
                project_file = ProjectFile(
                    run_id=run_id,
                    filename=file,
                    filepath=rel_path,
                    detected_lang=lang,
                    status=FileStatus.PENDING_CONFIRMATION
                )
                self.db.add(project_file)
                mapped_files.append({"file": file, "lang": lang})
        
        self.db.commit()
        return mapped_files
    def process_folder(self, run_id: str, folder_path: str):
        # For GitHub, the folder is already cloned, we just map it
        return self.map_files_to_db(run_id, folder_path)