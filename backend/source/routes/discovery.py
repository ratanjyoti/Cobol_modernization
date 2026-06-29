from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Processes.discovery_process import DiscoveryProcess
from Persistence.sqlite.session import get_db
import git # pip install GitPython
import os
import shutil

router = APIRouter(prefix="/discovery", tags=["Discovery"])

@router.post("/github")
async def ingest_github_repo(data: dict, db: Session = Depends(get_db)):
    run_id = data.get("run_id")
    repo_url = data.get("url")
    
    if not run_id or not repo_url:
        raise HTTPException(status_code=400, detail="Missing run_id or repo_url")

    try:
        # 1. Define paths
        temp_clone_path = f"data/uploads/temp_{run_id}"
        project_folder = f"data/uploads/{run_id}"

        # 2. Clone the repository
        if os.path.exists(temp_clone_path):
            shutil.rmtree(temp_clone_path)
        
        git.Repo.clone_from(repo_url, temp_clone_path)

        # 3. Use the same DiscoveryProcess we built in the previous step
        discovery = DiscoveryProcess(db)
        
        # We modify the process_upload slightly to take a folder instead of a ZIP
        # If you haven't modified process_upload, you can just move the files
        # and then treat it like a folder.
        
        # Let's assume we add a 'process_folder' method to DiscoveryProcess:
        mapped_files = discovery.process_folder(run_id, temp_clone_path)
        
        # Cleanup temp clone
        shutil.rmtree(temp_clone_path)

        return {"status": "GitHub Repo Ingested", "files_count": len(mapped_files)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git clone failed: {str(e)}")
