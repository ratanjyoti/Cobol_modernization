import sqlite3
import uuid
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="data/sqlite/system.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Users table
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT UNIQUE,
                                password_hash TEXT)''')
            
            # Projects table (The run_id tracker)
            cursor.execute('''CREATE TABLE IF NOT EXISTS projects (
                                run_id TEXT PRIMARY KEY,
                                user_id INTEGER,
                                llm_provider TEXT,
                                interaction_lang TEXT,
                                speed_profile TEXT,
                                reasoning_effort TEXT,
                                parallel_workers INTEGER,
                                created_at TEXT,
                                FOREIGN KEY(user_id) REFERENCES users(id))''')
            conn.commit()

    def create_user(self, username, hashed_password):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                           (username, hashed_password))
            conn.commit()

    def authenticate_user(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
            return cursor.fetchone()

    def create_project(self, project_data):
        run_id = str(uuid.uuid4())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO projects 
                             (run_id, user_id, llm_provider, interaction_lang, speed_profile, reasoning_effort, parallel_workers, created_at) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                           (run_id, project_data['user_id'], project_data['llm_provider'], 
                            project_data['interaction_lang'], project_data['speed_profile'], 
                            project_data['reasoning_effort'], project_data['parallel_workers'], 
                            datetime.now().isoformat()))
            conn.commit()
        return run_id

db = DatabaseManager()
