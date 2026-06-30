from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from Processes.discovery_process import DiscoveryProcess
from Persistence.sqlite.session import get_db
from Persistence.sqlite.models import FileStatus, ProjectFile
import shutil
import os
import asyncio
import stat
import subprocess
from pathlib import Path
from source.websockets.socket_manager import manager

router = APIRouter(prefix="/discovery", tags=["Discovery"])

def path_safe(filename: str | None) -> str:
    return os.path.basename(filename or "upload.zip")

def save_file_sync(upload_file: UploadFile, destination: Path):
    """Helper for asyncio.to_thread"""
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

def remove_tree_sync(path: Path):
    def handle_remove_error(func, failed_path, _exc_info):
        os.chmod(failed_path, stat.S_IWRITE)
        func(failed_path)

    if path.exists():
        shutil.rmtree(path, onerror=handle_remove_error)

@router.post("/upload-zip")
async def upload_zip(
    run_id: str = Form(...),
    zip_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not zip_file.filename or not zip_file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_zip_path = upload_dir / f"temp_{run_id}.zip"

    try:
        # Save file without blocking the event loop
        await asyncio.to_thread(save_file_sync, zip_file, temp_zip_path)

        discovery = DiscoveryProcess(db)
        # !!! ADDED AWAIT HERE !!!
        mapped_files = await discovery.process_zip_upload(run_id, str(temp_zip_path))
        return {"status": "Success", "mapped_files": mapped_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing zip: {str(e)}")
    finally:
        if temp_zip_path.exists():
            os.remove(temp_zip_path)

@router.post("/github")
async def ingest_github_repo(
    data: dict,
    db: Session = Depends(get_db)
):
    run_id = data.get("run_id")
    repo_url = data.get("url")

    if not run_id or not repo_url:
        raise HTTPException(status_code=400, detail="Missing run_id or url")

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_clone_path = upload_dir / f"temp_{run_id}"

    try:
        await asyncio.to_thread(remove_tree_sync, temp_clone_path)

        clone_cmd = ["git", "clone", "--depth", "1", repo_url, str(temp_clone_path)]
        result = await asyncio.to_thread(
            subprocess.run,
            clone_cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Git clone failed: {(result.stderr or result.stdout).strip()}",
            )

        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.process_folder(run_id, str(temp_clone_path))
        return {"status": "Success", "mapped_files": mapped_files}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git clone failed: {str(e)}")
    finally:
        await asyncio.to_thread(remove_tree_sync, temp_clone_path)

@router.post("/upload")
async def upload_source(
    run_id: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    zip_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    discovery = DiscoveryProcess(db)

    if zip_file:
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_path = upload_dir / path_safe(zip_file.filename)
        
        try:
            await asyncio.to_thread(save_file_sync, zip_file, temp_path)
            # !!! ADDED AWAIT HERE !!!
            mapped_files = await discovery.process_upload(run_id, str(temp_path))
        finally:
            if temp_path.exists():
                os.remove(temp_path)
    elif files:
        # !!! ADDED AWAIT HERE !!!
        mapped_files = await discovery.process_individual_files(run_id, files)
    else:
        raise HTTPException(status_code=400, detail="No files uploaded")

    return {"status": "Success", "mapped_files": mapped_files}

@router.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await manager.connect(websocket, run_id)
    try:
        while True:
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)

@router.post("/confirm-language")
async def confirm_language(data: dict, db: Session = Depends(get_db)):
    # This remains synchronous because it's a simple DB update
    run_id = data.get("run_id")
    filename = data.get("filename")
    lang = data.get("lang")

    if not all([run_id, filename, lang]):
        raise HTTPException(status_code=400, detail="Missing run_id, filename, or lang")

    try:
        file_record = db.query(ProjectFile).filter(
            ProjectFile.run_id == run_id, 
            ProjectFile.filename == filename
        ).first()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found in database")

        file_record.detected_lang = lang
        file_record.status = FileStatus.CONFIRMED
        db.commit()
        return {"status": "Success", "message": f"Language updated to {lang} for {filename}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")



