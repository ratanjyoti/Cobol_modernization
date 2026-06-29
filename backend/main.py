from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock database for local development.
projects_db = {}


@app.post("/projects")
async def create_project(config: dict):
    run_count = len(projects_db) + 1
    run_id = f"run{run_count}"

    projects_db[run_id] = {
        "run_id": run_id,
        "name": config.get("project_name", "New Project"),
        "status": "Running",
        "config": config,
        "files": [],
    }
    return projects_db[run_id]


@app.get("/projects")
async def list_projects():
    return [
        {
            "run_id": project["run_id"],
            "name": project["name"],
            "status": project["status"],
        }
        for project in projects_db.values()
    ]


@app.get("/projects/{run_id}/files")
async def list_project_files(run_id: str):
    project = projects_db.get(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"files": project.get("files", [])}


@app.patch("/projects/{run_id}/status")
async def update_status(run_id: str, status: str):
    project = projects_db.get(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project["status"] = status
    return {"status": "success", "new_status": status}


@app.patch("/projects/{run_id}/config")
async def update_config(run_id: str, config: dict):
    project = projects_db.get(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project["config"].update(config)
    return {"status": "success"}


@app.post("/discovery/upload")
async def upload_files(run_id: str = Form(...), files: List[UploadFile] = File(...)):
    project = projects_db.get(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mapped_files = []
    for file in files:
        contents = await file.read()
        mapped_file = {
            "id": uuid.uuid4().hex[:8],
            "filename": file.filename,
            "size": len(contents),
            "status": "PENDING_CONFIRMATION",
        }
        mapped_files.append(mapped_file)

    project["files"].extend(mapped_files)
    return {"status": "success", "mapped_files": mapped_files}


@app.post("/discovery/launch")
async def launch_pipeline(
    run_id: str = Form(...),
    scope: str = Form(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
):
    project = projects_db.get(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project["status"] = "Processing"
    project["config"].update({
        "scope": scope,
        "source_lang": source_lang,
        "target_lang": target_lang,
    })
    return {"status": "Pipeline Launched", "run_id": run_id}


@app.post("/discovery/github")
async def ingest_github(data: dict):
    run_id = data.get("run_id")
    repo_url = data.get("url")

    project = projects_db.get(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not repo_url:
        raise HTTPException(status_code=400, detail="Repository URL is required")

    mapped_files = [
        {
            "id": uuid.uuid4().hex[:8],
            "filename": "repo-placeholder.cbl",
            "size": 0,
            "status": "PENDING_CONFIRMATION",
        }
    ]
    project["files"].extend(mapped_files)
    return {"status": "success", "mapped_files": mapped_files}
