import os
import zipfile
import shutil
from git import Repo # pip install gitpython
from paths import STORAGE_DIR

STORAGE_PATH = str(STORAGE_DIR)

class IngestionService:
    @staticmethod
    def get_project_path(run_id: str):
        path = os.path.join(STORAGE_PATH, run_id)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def process_zip(run_id: str, zip_file):
        project_path = IngestionService.get_project_path(run_id)
        zip_path = os.path.join(project_path, "upload.zip")
        
        # Save the uploaded zip file physically
        with open(zip_path, "wb") as f:
            f.write(zip_file.file.read())

        # Extract the zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(project_path)
        
        # Delete the zip after extraction
        os.remove(zip_path)
        
        return IngestionService.list_files(project_path)

    @staticmethod
    def process_github(run_id: str, repo_url: str):
        project_path = IngestionService.get_project_path(run_id)
        
        # Clear folder if it exists to avoid Git errors
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
            
        # Clone the repository
        Repo.clone_from(repo_url, project_path)
        
        return IngestionService.list_files(project_path)

    @staticmethod
    def list_files(path):
        file_list = []
        # Walk through the extracted folder to find all files
        for root, dirs, files in os.walk(path):
            for file in files:
                # Ignore hidden git folders
                if ".git" in root: continue
                
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, path)
                
                file_list.append({
                    "id": f"file_{hash(full_path)}",
                    "filename": relative_path,
                    "size": os.path.getsize(full_path)
                })
        return file_list
