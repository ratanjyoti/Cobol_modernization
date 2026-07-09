import re

class ResolutionService:
    def __init__(self, db_session):
        self.db = db_session
        self.phonebook = {} # Map of CleanName -> FileID

    def build_phonebook(self, run_id: str):
        """
        Scans SQLite for all files in the project and creates a clean mapping.
        'CUSTOMER-INQUIRY.cbl' -> 'CUSTOMERINQUIRY'
        """
        from Persistence.sqlite.models import ProjectFile
        files = self.db.query(ProjectFile).filter_by(run_id=run_id).all()
        
        for f in files:
            # Clean the name: Remove extension, remove dashes, uppercase
            clean_name = os.path.splitext(f.filename)[0].replace('-', '').upper()
            self.phonebook[clean_name] = {
                "id": f.id, 
                "original_name": f.filename, 
                "ext": os.path.splitext(f.filename)[1]
            }
        return self.phonebook

    def resolve(self, raw_name: str):
        """Clean a found keyword and find the actual file ID from the phonebook."""
        clean_raw = raw_name.replace("'", "").replace('"', "").replace('-', '').upper()
        return self.phonebook.get(clean_raw)
