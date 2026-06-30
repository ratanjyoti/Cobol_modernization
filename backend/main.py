from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from Persistence.sqlite.session import init_db

# Initialize the database
init_db()

# Import the routers from your routes folder
from source.routes import project, discovery

app = FastAPI(
    title="ModernizerAI Backend",
    description="Enterprise Legacy Migration Pipeline",
    version="1.0.0"
)

# ==============================================================================
# 1. CORS CONFIGURATION
# ==============================================================================
# This allows your React frontend (usually on port 3000 or 5173) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with ["http://localhost:3000"]
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
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # Run the server on localhost:8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
