import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from Persistence.sqlite.session import get_db
from Persistence.sqlite.models import BusinessRule, Project
from Processes.logic_extraction_process import LogicExtractionProcess

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from Persistence.sqlite.session import init_db
from fastapi.middleware.cors import CORSMiddleware

# Initialize the database
init_db()

# Import the routers from your routes folder
from source.routes import project, discovery, business_rule_routes, llm_health

app = FastAPI(
    title="ModernizerAI Backend",
    description="Enterprise Legacy Migration Pipeline",
    version="1.0.0"
)

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://cobol-modernization-green.vercel.app",
    "https://cobol-modernization-git-main-rjrk9793s-projects.vercel.app",
    "https://cobol-modernization.onrender.com",
]


def get_allowed_origins():
    configured_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return sorted(set(DEFAULT_ALLOWED_ORIGINS + configured_origins))


# ==============================================================================
# 1. CORS CONFIGURATION
# ==============================================================================
# This allows the React frontend to talk to this API from local and deployed hosts.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 2. ROUTER REGISTRATION
# ==============================================================================
# Instead of writing logic here, we "include" the specialized routers.
# This is why your /discovery/upload-zip was not found; it wasn't included here.

# Project Onboarding Routes (/projects/create, /projects/config, etc.)
app.include_router(project.router)

# Discovery & Ingestion Routes (/discovery/upload-zip, /discovery/github, etc.)
app.include_router(discovery.router)
app.include_router(business_rule_routes.router)
app.include_router(llm_health.router)

# ==============================================================================
# 3. GLOBAL ERROR HANDLING
# ==============================================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid data sent to server. Please check your request format."},
    )

# ==============================================================================
# 4. HEALTH CHECK
# ==============================================================================
@app.get("/")
async def root():
    return {
        "status": "Online",
        "message": "ModernizerAI Backend is running",
        "documentation": "/docs",
        "build": "byok-health-v2"
    }
analysis_router = APIRouter(prefix="/analysis", tags=["Analysis"])

@analysis_router.post("/extract-rules/{run_id}")
async def trigger_extraction(run_id: str, db: Session = Depends(get_db)):
    """
    Triggers the Two-Pass Business Logic Extraction process.
    """
    try:
        # 1. Fetch project settings to know which LLM provider to use
        project = db.query(Project).filter_by(run_id=run_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project run not found")
        
        llm_provider = project.llm_provider or "local"
        # Pull API key from .env if using OpenRouter
        api_key = os.getenv("OPENROUTER_API_KEY") 

        # 2. Initialize the Process Orchestrator
        process = LogicExtractionProcess(db, llm_provider, api_key)
        
        # 3. Execute the extraction pipeline
        rules_count = await process.extract_all_rules(run_id)
        
        return {
            "status": "success", 
            "message": f"Extraction complete. {rules_count} rules generated.",
            "rules_count": rules_count
        }
    except Exception as e:
        print(f"Extraction Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@analysis_router.get("/business-rules/{run_id}")
async def get_rules(run_id: str, db: Session = Depends(get_db)):
    """
    Fetches all extracted rules for the Evidence Panel in the UI.
    """
    rules = db.query(BusinessRule).filter_by(run_id=run_id).all()
    
    return [
        {
            "id": r.id,
            "rule_id": r.rule_id,
            "rule_text": r.rule_text,
            "technical_ref": r.technical_ref,
            "technical_yaml": r.technical_yaml,
            "status": r.status,
            "chunk_index": r.chunk_index
        } for r in rules
    ]

@analysis_router.patch("/confirm-rule/{rule_id}")
async def confirm_rule(rule_id: int, data: dict, db: Session = Depends(get_db)):
    """
    Updates a rule's status (PENDING -> VERIFIED) or updates the text.
    """
    rule = db.query(BusinessRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update status (e.g., 'VERIFIED' or 'REJECTED')
    if "status" in data:
        rule.status = data["status"]
    
    # Update text if the human expert edited the rule
    if "text" in data:
        rule.rule_text = data["text"]
        rule.business_logic = data["text"]
        
    db.commit()
    return {"status": "success", "message": "Rule updated successfully"}

# IMPORTANT: Add this to your FastAPI app instance in main.py
# app.include_router(analysis_router)

if __name__ == "__main__":
    import uvicorn
    # Run the server on localhost:8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


