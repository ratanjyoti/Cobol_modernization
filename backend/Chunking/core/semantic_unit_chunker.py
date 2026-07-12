import json
from Chunking.adapters.cobol_adapter import CobolAdapter
from Chunking.adapters.fortran_adapter import FortranAdapter
from Chunking.adapters.jcl_adapter import JclAdapter
from Chunking.adapters.pli_adapter import PLIAdapter
from Chunking.adapters.telon_adapter import TelonAdapter
from Chunking.core.settings import ChunkingSettings, normalize_language


class SemanticUnitChunker:
    def __init__(self, max_lines: int | None = None, overlap: int | None = None):
        settings = ChunkingSettings()
        self.max_lines = max_lines or settings.max_lines_per_chunk
        self.overlap = overlap or settings.overlap_lines
        self.adapters = {
            "COBOL": CobolAdapter(),
            "JCL": JclAdapter(),
            "TELON": TelonAdapter(),
            "PLI": PLIAdapter(),
            "FORTRAN": FortranAdapter(),
        }

    def slice_content(self, content: str, lang: str):
        lines = content.splitlines()
        if not lines:
            return []

        units = self._semantic_units(content, lang)
        chunks = []
        current_start = None
        current_end = None
        current_units = []

        for unit in units:
            unit_start = unit["start_line"]
            unit_end = unit["end_line"]
            unit_lines = unit_end - unit_start + 1

            if unit_lines > self.max_lines:
                if current_units:
                    chunks.append(self._build_chunk(lines, current_start, current_end, current_units))
                    current_start = current_end = None
                    current_units = []
                chunks.extend(self._hard_cut_unit(lines, unit))
                continue

            if current_start is None:
                current_start = unit_start
                current_end = unit_end
                current_units = [unit]
                continue

            would_end = unit_end
            if would_end - current_start + 1 > self.max_lines:
                chunks.append(self._build_chunk(lines, current_start, current_end, current_units))
                current_start = unit_start
                current_end = unit_end
                current_units = [unit]
            else:
                current_end = unit_end
                current_units.append(unit)

        if current_units:
            chunks.append(self._build_chunk(lines, current_start, current_end, current_units))

        return [self._with_overlap(lines, chunk) for chunk in chunks]

    def _semantic_units(self, content: str, lang: str) -> list[dict]:
        normalized = normalize_language(lang)
        adapter = self.adapters.get(normalized)
        if not adapter:
            total_lines = len(content.splitlines())
            return [{"name": "FILE", "kind": "file", "start_line": 1, "end_line": total_lines}]
        return adapter.identify_structure(content)

    def _build_chunk(self, lines: list[str], start_line: int, end_line: int, units: list[dict]) -> dict:
        return {
            "start": start_line,
            "end": end_line,
            "content": "\n".join(lines[start_line - 1:end_line]),
            "semantic_units": [f"{unit['kind']}:{unit['name']}" for unit in units],
            "overlap": "",
        }

    def _with_overlap(self, lines: list[str], chunk: dict) -> dict:
        overlap_start = max(1, chunk["start"] - self.overlap)
        chunk["overlap"] = "\n".join(lines[overlap_start - 1:chunk["start"] - 1])
        return chunk

    def _hard_cut_unit(self, lines: list[str], unit: dict) -> list[dict]:
        chunks = []
        start = unit["start_line"]
        while start <= unit["end_line"]:
            end = min(start + self.max_lines - 1, unit["end_line"])
            chunks.append(self._build_chunk(lines, start, end, [{
                "kind": f"{unit['kind']}-fragment",
                "name": unit["name"],
                "start_line": start,
                "end_line": end,
            }]))
            start = end + 1
        return chunks

    @staticmethod
    def semantic_units_json(chunk: dict) -> str:
        return json.dumps(chunk.get("semantic_units", []))

