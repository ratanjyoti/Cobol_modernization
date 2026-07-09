import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("MODERNIZER_DATA_DIR", BACKEND_DIR / "data"))
UPLOADS_DIR = DATA_DIR / "uploads"
SQLITE_DIR = DATA_DIR / "sqlite"
SQLITE_DB_PATH = SQLITE_DIR / "modernizer.db"
STORAGE_DIR = Path(os.getenv("MODERNIZER_STORAGE_DIR", DATA_DIR / "storage" / "projects"))
