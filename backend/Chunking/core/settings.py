import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingSettings:
    auto_chunk_char_threshold: int = int(os.getenv("AUTO_CHUNK_CHAR_THRESHOLD", "150000"))
    auto_chunk_line_threshold: int = int(os.getenv("AUTO_CHUNK_LINE_THRESHOLD", "3000"))
    max_lines_per_chunk: int = int(os.getenv("MAX_LINES_PER_CHUNK", "1500"))
    overlap_lines: int = int(os.getenv("OVERLAP_LINES", "300"))
    max_parallel_chunks: int = int(os.getenv("MAX_PARALLEL_CHUNKS", "5"))
    token_budget_per_minute: int = int(os.getenv("TOKEN_BUDGET_PER_MINUTE", "60000"))
    rate_limit_safety_factor: float = float(os.getenv("RATE_LIMIT_SAFETY_FACTOR", "0.8"))


def normalize_language(lang: str | None) -> str:
    value = (lang or "").strip().lower()
    if value.startswith("cobol"):
        return "COBOL"
    if value.startswith("jcl"):
        return "JCL"
    if value.startswith("telon"):
        return "TELON"
    if value in {"pli", "pl/i", "pl1"}:
        return "PLI"
    if value.startswith("fortran"):
        return "FORTRAN"
    if value in {"vb.net", "vbnet", "vb", "visual-basic"}:
        return "VB.NET"
    if value in {"c#", "csharp", "cs"}:
        return "C#"
    if value == "sql":
        return "SQL"
    return value.upper() if value else "UNKNOWN"
