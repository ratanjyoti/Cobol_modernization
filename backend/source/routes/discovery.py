from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from Processes.discovery_process import DiscoveryProcess
from Persistence.sqlite.session import get_db
import shutil
import os

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.post("/upload-zip")
async def upload_zip(
    run_id: str = Form(...),
    zip_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not zip_file.filename or not zip_file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")

    os.makedirs("data/uploads", exist_ok=True)
    temp_zip_path = f"data/uploads/temp_{run_id}.zip"
    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(zip_file.file, buffer)

    try:
        discovery = DiscoveryProcess(db)
        mapped_files = discovery.process_zip_upload(run_id, temp_zip_path)
        return {"status": "Success", "mapped_files": mapped_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing zip: {str(e)}")
    finally:
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)


@router.post("/github")
async def ingest_github_repo(data: dict, db: Session = Depends(get_db)):
    run_id = data.get("run_id")
    repo_url = data.get("url")

    if not run_id or not repo_url:
        raise HTTPException(status_code=400, detail="Missing run_id or repo_url")

    try:
        import git
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="GitPython is not installed. Install it with: pip install GitPython",
        ) from exc

    temp_clone_path = f"data/uploads/temp_{run_id}"
    try:
        if os.path.exists(temp_clone_path):
            shutil.rmtree(temp_clone_path)

        git.Repo.clone_from(repo_url, temp_clone_path)
        discovery = DiscoveryProcess(db)
        mapped_files = discovery.process_folder(run_id, temp_clone_path)
        return {"status": "GitHub Repo Ingested", "mapped_files": mapped_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git clone failed: {str(e)}")
    finally:
        if os.path.exists(temp_clone_path):
            shutil.rmtree(temp_clone_path)


@router.post("/upload")
async def upload_source(
    run_id: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    zip_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    discovery = DiscoveryProcess(db)

    if zip_file:
        os.makedirs("data/uploads", exist_ok=True)
        temp_path = f"data/uploads/{PathSafe(zip_file.filename)}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(zip_file.file, buffer)
        try:
            mapped_files = discovery.process_upload(run_id, temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    elif files:
        mapped_files = await discovery.process_individual_files(run_id, files)
    else:
        raise HTTPException(status_code=400, detail="No files uploaded")

    return {"status": "Success", "mapped_files": mapped_files}


def PathSafe(filename: str | None) -> str:
    return os.path.basename(filename or "upload.zip")
