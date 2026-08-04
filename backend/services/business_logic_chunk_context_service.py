from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class BusinessLogicChunkSource:
    chunk_index: int | str
    primary_start_line: int
    primary_end_line: int
    overlap_start_line: int | None
    overlap_end_line: int | None
    overlap_source: str
    primary_source: str
    semantic_units: list[str]
    request_index: int = 0
    parent_chunk_index: int | None = None


def build_chunk_source(chunk: Any) -> BusinessLogicChunkSource:
    overlap = str(getattr(chunk, "overlap_content", "") or "")
    combined = str(getattr(chunk, "content", "") or "")

    primary = combined
    if overlap:
        prefix = overlap + "\n"
        if combined.startswith(prefix):
            primary = combined[len(prefix):]

    overlap_line_count = len(overlap.splitlines()) if overlap else 0
    primary_start_line = int(getattr(chunk, "start_line", None) or 1)
    primary_end_line = int(getattr(chunk, "end_line", None) or primary_start_line)
    overlap_start = max(1, primary_start_line - overlap_line_count) if overlap_line_count else None

    try:
        semantic_units = json.loads(getattr(chunk, "semantic_units", "") or "[]")
    except (TypeError, json.JSONDecodeError):
        semantic_units = []

    if not isinstance(semantic_units, list):
        semantic_units = []

    return BusinessLogicChunkSource(
        chunk_index=int(getattr(chunk, "chunk_index", 0) or 0),
        primary_start_line=primary_start_line,
        primary_end_line=primary_end_line,
        overlap_start_line=overlap_start,
        overlap_end_line=primary_start_line - 1 if overlap_line_count else None,
        overlap_source=overlap,
        primary_source=primary,
        semantic_units=[str(item) for item in semantic_units],
        parent_chunk_index=int(getattr(chunk, "chunk_index", 0) or 0),
    )


def number_source(text: str, start_line: int) -> str:
    return "\n".join(
        f"{line_number:06d}: {line}"
        for line_number, line in enumerate((text or "").splitlines(), start=start_line)
    )


def format_chunk_for_prompt(chunk_source: BusinessLogicChunkSource) -> str:
    sections: list[str] = []

    if chunk_source.overlap_source:
        sections.append(
            "CONTEXT-ONLY SOURCE\n"
            "Use this only to understand preceding control flow.\n"
            "Do not generate persistent business rules from this section.\n\n"
            + number_source(
                chunk_source.overlap_source,
                chunk_source.overlap_start_line or 1,
            )
        )

    sections.append(
        "PRIMARY SOURCE\n"
        "Extract business rules only from this section.\n\n"
        + number_source(
            chunk_source.primary_source,
            chunk_source.primary_start_line,
        )
    )

    return "\n\n".join(sections)


def split_chunk_source_for_prompt_budget(
    chunk_source: BusinessLogicChunkSource,
    max_primary_chars: int,
) -> list[BusinessLogicChunkSource]:
    primary_lines = chunk_source.primary_source.splitlines()
    if len(chunk_source.primary_source) <= max_primary_chars or not primary_lines:
        return [chunk_source]

    batches: list[BusinessLogicChunkSource] = []
    current_lines: list[str] = []
    current_start = chunk_source.primary_start_line
    request_index = 1

    for offset, line in enumerate(primary_lines):
        line_no = chunk_source.primary_start_line + offset
        next_size = len("\n".join([*current_lines, line]))
        if current_lines and next_size > max_primary_chars:
            batches.append(
                BusinessLogicChunkSource(
                    chunk_index=f"{chunk_source.chunk_index}.{request_index}",
                    primary_start_line=current_start,
                    primary_end_line=line_no - 1,
                    overlap_start_line=chunk_source.overlap_start_line,
                    overlap_end_line=chunk_source.overlap_end_line,
                    overlap_source=chunk_source.overlap_source,
                    primary_source="\n".join(current_lines),
                    semantic_units=chunk_source.semantic_units,
                    request_index=request_index,
                    parent_chunk_index=int(chunk_source.parent_chunk_index or 0),
                )
            )
            request_index += 1
            current_lines = []
            current_start = line_no
        current_lines.append(line)

    if current_lines:
        batches.append(
            BusinessLogicChunkSource(
                chunk_index=f"{chunk_source.chunk_index}.{request_index}",
                primary_start_line=current_start,
                primary_end_line=current_start + len(current_lines) - 1,
                overlap_start_line=chunk_source.overlap_start_line,
                overlap_end_line=chunk_source.overlap_end_line,
                overlap_source=chunk_source.overlap_source,
                primary_source="\n".join(current_lines),
                semantic_units=chunk_source.semantic_units,
                request_index=request_index,
                parent_chunk_index=int(chunk_source.parent_chunk_index or 0),
            )
        )

    return batches


def chunk_diagnostics(chunks: list[Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for chunk in chunks:
        overlap = str(getattr(chunk, "overlap_content", "") or "")
        content = str(getattr(chunk, "content", "") or "")
        diagnostics.append(
            {
                "chunk_id": getattr(chunk, "id", None),
                "chunk_index": getattr(chunk, "chunk_index", None),
                "primary_start_line": getattr(chunk, "start_line", None),
                "primary_end_line": getattr(chunk, "end_line", None),
                "total_lines": len(content.splitlines()),
                "overlap_lines": len(overlap.splitlines()) if overlap else 0,
                "chars": len(content),
                "content_contains_overlap_prefix": bool(overlap) and content.startswith(overlap + "\n"),
                "semantic_units": getattr(chunk, "semantic_units", "") or "[]",
            }
        )
    return diagnostics
