from Chunking.core.settings import ChunkingSettings


class SizingRouter:
    DEFAULT_SETTINGS = ChunkingSettings()
    MAX_LINES = DEFAULT_SETTINGS.auto_chunk_line_threshold
    MAX_CHARS = DEFAULT_SETTINGS.auto_chunk_char_threshold

    @staticmethod
    def analyze_content(content: str) -> dict:
        return {
            "total_characters": len(content),
            "total_lines": content.count("\n") + (1 if content else 0),
        }

    @staticmethod
    def analyze_file(file_path: str, chunk_size: int = 1024 * 1024) -> dict:
        total_chars = 0
        total_lines = 0
        saw_content = False
        with open(file_path, "r", errors="ignore") as handle:
            while True:
                block = handle.read(chunk_size)
                if not block:
                    break
                saw_content = True
                total_chars += len(block)
                total_lines += block.count("\n")
        if saw_content:
            total_lines += 1
        return {"total_characters": total_chars, "total_lines": total_lines}

    @staticmethod
    def needs_chunking(content: str, settings: ChunkingSettings | None = None) -> bool:
        settings = settings or SizingRouter.DEFAULT_SETTINGS
        metrics = SizingRouter.analyze_content(content)
        return (
            metrics["total_lines"] > settings.auto_chunk_line_threshold
            or metrics["total_characters"] > settings.auto_chunk_char_threshold
        )

    @staticmethod
    def file_needs_chunking(file_path: str, settings: ChunkingSettings | None = None) -> bool:
        settings = settings or SizingRouter.DEFAULT_SETTINGS
        metrics = SizingRouter.analyze_file(file_path)
        return (
            metrics["total_lines"] > settings.auto_chunk_line_threshold
            or metrics["total_characters"] > settings.auto_chunk_char_threshold
        )
