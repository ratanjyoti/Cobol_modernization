# FastAPI Entry Point
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.api.v1 import auth, project, ingestion
from app.core.websocket import ConnectionManager

app = FastAPI(title="Legacy Modernization Engine")
manager = ConnectionManager() # Handles WebSocket alerts

# Include Routes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(project.router, prefix="/project", tags=["Project Config"])
app.include_router(ingestion.router, prefix="/ingest", tags=["Ingestion"])

@app.websocket("/ws/alerts/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    return {"status": "Backend Online", "version": "1.0.0"}

from fastapi import FastAPI
from app.api.v1 import auth, project

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(project.router, prefix="/project", tags=["Project"])
