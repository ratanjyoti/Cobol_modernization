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
    ensure_schema_columns()
    ensure_indexes()


def _table_columns(connection, table_name: str) -> set[str]:
    return {row[1] for row in connection.execute(text(f"PRAGMA table_info({table_name})"))}


def _add_missing_columns(connection, table_name: str, column_statements: dict[str, str]):
    existing_columns = _table_columns(connection, table_name)
    for column_name, statement in column_statements.items():
        if column_name not in existing_columns:
            connection.execute(text(statement))


def ensure_schema_columns():
    with engine.begin() as connection:
        _add_missing_columns(connection, "projects", {
            "ai_mode": "ALTER TABLE projects ADD COLUMN ai_mode VARCHAR",
            "custom_api_key": "ALTER TABLE projects ADD COLUMN custom_api_key VARCHAR",
            "custom_api_base_url": "ALTER TABLE projects ADD COLUMN custom_api_base_url VARCHAR",
            "neo4j_uri": "ALTER TABLE projects ADD COLUMN neo4j_uri VARCHAR",
            "neo4j_user": "ALTER TABLE projects ADD COLUMN neo4j_user VARCHAR",
            "neo4j_password": "ALTER TABLE projects ADD COLUMN neo4j_password VARCHAR",
        })
        _add_missing_columns(connection, "file_complexity", {
            "mode": "ALTER TABLE file_complexity ADD COLUMN mode VARCHAR",
            "multiplier": "ALTER TABLE file_complexity ADD COLUMN multiplier FLOAT",
            "calculation": "ALTER TABLE file_complexity ADD COLUMN calculation TEXT",
        })
        _add_missing_columns(connection, "file_chunks", {
            "semantic_units": "ALTER TABLE file_chunks ADD COLUMN semantic_units TEXT",
            "converted_code": "ALTER TABLE file_chunks ADD COLUMN converted_code TEXT",
            "summary": "ALTER TABLE file_chunks ADD COLUMN summary TEXT",
            "tokens_used": "ALTER TABLE file_chunks ADD COLUMN tokens_used INTEGER DEFAULT 0",
            "processing_time": "ALTER TABLE file_chunks ADD COLUMN processing_time FLOAT DEFAULT 0",
            "status": "ALTER TABLE file_chunks ADD COLUMN status VARCHAR DEFAULT 'PENDING'",
            "error_message": "ALTER TABLE file_chunks ADD COLUMN error_message TEXT",
        })
        _add_missing_columns(connection, "business_rules", {
            "chunk_id": "ALTER TABLE business_rules ADD COLUMN chunk_id INTEGER",
            "rule_id": "ALTER TABLE business_rules ADD COLUMN rule_id VARCHAR",
            "rule_text": "ALTER TABLE business_rules ADD COLUMN rule_text TEXT",
            "technical_ref": "ALTER TABLE business_rules ADD COLUMN technical_ref TEXT",
            "file_id": "ALTER TABLE business_rules ADD COLUMN file_id INTEGER",
            "chunk_index": "ALTER TABLE business_rules ADD COLUMN chunk_index INTEGER",
            "technical_yaml": "ALTER TABLE business_rules ADD COLUMN technical_yaml TEXT",
            "business_purpose": "ALTER TABLE business_rules ADD COLUMN business_purpose TEXT",
            "functional_logic": "ALTER TABLE business_rules ADD COLUMN functional_logic TEXT",
            "business_logic": "ALTER TABLE business_rules ADD COLUMN business_logic TEXT",
        })
        _add_missing_columns(connection, "type_mapping_table", {
            "file_id": "ALTER TABLE type_mapping_table ADD COLUMN file_id INTEGER",
            "legacy_type": "ALTER TABLE type_mapping_table ADD COLUMN legacy_type VARCHAR",
            "target_type": "ALTER TABLE type_mapping_table ADD COLUMN target_type VARCHAR",
            "target_field_name": "ALTER TABLE type_mapping_table ADD COLUMN target_field_name VARCHAR",
        })
        _add_missing_columns(connection, "signature_registry", {
            "file_id": "ALTER TABLE signature_registry ADD COLUMN file_id INTEGER",
            "target_method_name": "ALTER TABLE signature_registry ADD COLUMN target_method_name VARCHAR",
            "target_signature": "ALTER TABLE signature_registry ADD COLUMN target_signature VARCHAR",
            "converted_chunk_index": "ALTER TABLE signature_registry ADD COLUMN converted_chunk_index INTEGER",
        })
        _add_missing_columns(connection, "consistency_discrepancies", {
            "file_id": "ALTER TABLE consistency_discrepancies ADD COLUMN file_id INTEGER",
            "chunk_index": "ALTER TABLE consistency_discrepancies ADD COLUMN chunk_index INTEGER",
        })


def ensure_indexes():
    index_statements = [
        "CREATE INDEX IF NOT EXISTS ix_project_files_run_id ON project_files (run_id)",
        "CREATE INDEX IF NOT EXISTS ix_project_files_run_id_status ON project_files (run_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_project_files_run_id_lang ON project_files (run_id, detected_lang)",
        "CREATE INDEX IF NOT EXISTS ix_file_relations_run_id ON file_relations (run_id)",
        "CREATE INDEX IF NOT EXISTS ix_file_chunks_run_id_file_id ON file_chunks (run_id, file_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_file_chunks_run_file_idx ON file_chunks (run_id, file_id, chunk_index)",
        "CREATE INDEX IF NOT EXISTS ix_file_complexity_run_id ON file_complexity (run_id)",
        "CREATE INDEX IF NOT EXISTS ix_type_mapping_run_file ON type_mapping_table (run_id, file_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_type_mapping_run_file_var ON type_mapping_table (run_id, file_id, legacy_variable)",
        "CREATE INDEX IF NOT EXISTS ix_signature_registry_run_file ON signature_registry (run_id, file_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_signature_registry_run_file_name ON signature_registry (run_id, file_id, legacy_name)",
        "CREATE INDEX IF NOT EXISTS ix_discrepancies_run_file ON consistency_discrepancies (run_id, file_id)",
    ]

    with engine.begin() as connection:
        _add_missing_columns(connection, "projects", {
            "ai_mode": "ALTER TABLE projects ADD COLUMN ai_mode VARCHAR",
            "custom_api_key": "ALTER TABLE projects ADD COLUMN custom_api_key VARCHAR",
            "custom_api_base_url": "ALTER TABLE projects ADD COLUMN custom_api_base_url VARCHAR",
            "neo4j_uri": "ALTER TABLE projects ADD COLUMN neo4j_uri VARCHAR",
            "neo4j_user": "ALTER TABLE projects ADD COLUMN neo4j_user VARCHAR",
            "neo4j_password": "ALTER TABLE projects ADD COLUMN neo4j_password VARCHAR",
        })
        for statement in index_statements:
            connection.execute(text(statement))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()






