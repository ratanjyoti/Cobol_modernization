from typing import List, Optional
import asyncio
import os
import shutil
import stat
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from Persistence.neo4j.graph_service import GraphService
from Persistence.sqlite.models import FileStatus, ProjectFile
from Persistence.sqlite.session import SessionLocal, get_db
from Processes.discovery_process import DiscoveryProcess
from Processes.graphing_process import GraphingProcess
from source.websockets.socket_manager import manager


router = APIRouter(prefix="/discovery", tags=["Discovery"])


def path_safe(filename: str | None) -> str:
    return os.path.basename(filename or "upload.zip")


def save_file_sync(upload_file: UploadFile, destination: Path):
    """Helper for asyncio.to_thread."""
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
        await asyncio.to_thread(save_file_sync, zip_file, temp_zip_path)
        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.process_zip_upload(run_id, str(temp_zip_path))
        return {"status": "Success", "mapped_files": mapped_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing zip: {str(e)}")
    finally:
        if temp_zip_path.exists():
            os.remove(temp_zip_path)


@router.post("/launch")
async def launch_pipeline(
    background_tasks: BackgroundTasks,
    run_id: str = Form(...),
    source_lang: str = Form(""),
    target_lang: str = Form(""),
    scope: str = Form(""),
):
    """
    Triggers the transition from ingestion to analysis and starts Neo4j graphing.
    """
    background_tasks.add_task(run_graphing_task, run_id)

    return {
        "status": "Pipeline Launched",
        "run_id": run_id,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "scope": scope,
        "parallel_tasks": ["Neo4j_Graphing"],
    }


def run_graphing_task(run_id: str):
    """Execute graphing with a fresh database session for the background task."""
    db = SessionLocal()
    try:
        graph_proc = GraphingProcess(db)
        graph_proc.build_full_graph(run_id)
        print(f"Graph successfully built for {run_id}")
    except Exception as e:
        print(f"Background Graphing Error for {run_id}: {str(e)}")
    finally:
        db.close()


@router.get("/impact-analysis/{item_name}")
async def get_impact_analysis(item_name: str):
    """
    Returns programs affected by the selected dependency item.
    """
    graph_service = None
    try:
        graph_service = GraphService()
        impacted_programs = graph_service.get_impacted_programs(item_name)

        return {
            "target": item_name,
            "impacted_programs": impacted_programs,
            "count": len(impacted_programs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if graph_service is not None:
            graph_service.close()


@router.post("/upload-folder")
async def upload_folder(
    run_id: str = Form(...),
    files: List[UploadFile] = File(...),
    paths: List[str] = Form(...),
    db: Session = Depends(get_db),
):
    try:
        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.process_folder_upload(run_id, files, paths)
        return {"status": "Success", "mapped_files": mapped_files}
    except Exception as e:
        print(f"Folder upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Folder upload failed: {str(e)}")


@router.post("/local-repo")
async def ingest_local_repo(
    run_id: str = Form(...),
    repo_path: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Ingests an existing local Git repository from the backend machine.
    The path must point to a folder containing a .git directory or file.
    """
    try:
        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.ingest_local_git_repo(run_id, repo_path)
        return {
            "status": "Success",
            "message": f"Successfully inventoried {len(mapped_files)} files from local repository",
            "mapped_files": mapped_files,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Local repository ingestion failed: {str(e)}")


@router.post("/github")
async def ingest_github(
    request: Request,
    run_id: Optional[str] = Form(None),
    repo_url: Optional[str] = Form(None),
    github_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Ingests a GitHub repository using the DiscoveryProcess logic.
    Accepts multipart form data from the current UI and JSON from older clients.
    """
    if run_id is None or repo_url is None:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
            run_id = run_id or payload.get("run_id")
            repo_url = repo_url or payload.get("repo_url") or payload.get("url")
            github_token = github_token or payload.get("github_token")

    if not run_id or not repo_url:
        raise HTTPException(status_code=400, detail="Missing run_id or repo_url")

    repo_url = repo_url.strip()
    github_token = github_token.strip() if github_token else None

    if not repo_url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL. Must be a github.com URL.")

    try:
        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.ingest_github_repo(run_id, repo_url, github_token)

        return {
            "status": "Success",
            "message": f"Successfully ingested {len(mapped_files)} files from GitHub",
            "mapped_files": mapped_files,
        }
    except Exception as e:
        print(f"GitHub Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub ingestion failed: {str(e)}")


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
            mapped_files = await discovery.process_upload(run_id, str(temp_path))
        finally:
            if temp_path.exists():
                os.remove(temp_path)
    elif files:
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
    run_id = data.get("run_id")
    filename = data.get("filename")
    lang = data.get("lang")

    if not all([run_id, filename, lang]):
        raise HTTPException(status_code=400, detail="Missing run_id, filename, or lang")

    try:
        file_record = db.query(ProjectFile).filter(
            ProjectFile.run_id == run_id,
            ProjectFile.filename == filename,
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
