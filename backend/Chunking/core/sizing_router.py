class SizingRouter:
    MAX_LINES = 3000
    MAX_CHARS = 150000

    @staticmethod
    def needs_chunking(content: str) -> bool:
        lines = content.splitlines()
        chars = len(content)
        
        if len(lines) > SizingRouter.MAX_LINES or chars > SizingRouter.MAX_CHARS:
            return True # Trigger Smart Chunking
        return False # Direct Processing
