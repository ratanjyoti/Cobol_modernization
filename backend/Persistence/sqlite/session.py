from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from paths import SQLITE_DB_PATH
from Persistence.sqlite.models import Base

SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH.as_posix()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)


@event.listens_for(engine, "connect")
def configure_sqlite_connection(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=OFF")
    cursor.execute("PRAGMA synchronous=OFF")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_indexes()


def ensure_indexes():
    index_statements = [
        "CREATE INDEX IF NOT EXISTS ix_project_files_run_id ON project_files (run_id)",
        "CREATE INDEX IF NOT EXISTS ix_project_files_run_id_status ON project_files (run_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_project_files_run_id_lang ON project_files (run_id, detected_lang)",
        "CREATE INDEX IF NOT EXISTS ix_file_relations_run_id ON file_relations (run_id)",
        "CREATE INDEX IF NOT EXISTS ix_file_chunks_run_id_file_id ON file_chunks (run_id, file_id)",
        "CREATE INDEX IF NOT EXISTS ix_file_complexity_run_id ON file_complexity (run_id)",
    ]

    with engine.begin() as connection:
        for statement in index_statements:
            connection.execute(text(statement))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
