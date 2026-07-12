import re
from pathlib import Path
from Chunking.core.reconciler import AssemblyService


class OutputWriter:
    CLASS_RE = re.compile(r"public\s+class\s+([A-Za-z_]\w*)")
    IMPORT_RE = re.compile(r"^\s*import\s+[^;]+;", re.MULTILINE)

    def __init__(self, db_session, output_dir: str | Path):
        self.db = db_session
        self.output_dir = Path(output_dir)

    def write_outputs(self, run_id: str, file_id: int, relative_source_path: str = "", class_name: str = "MigratedProgram") -> list[Path]:
        service = AssemblyService(self.db)
        code = service.assemble_file(run_id, file_id, class_name=class_name)
        target_dir = self.output_dir / Path(relative_source_path).parent
        target_dir.mkdir(parents=True, exist_ok=True)

        imports = "\n".join(sorted(set(match.group(0).strip() for match in self.IMPORT_RE.finditer(code))))
        class_blocks = self._split_classes(code)
        written = []

        if not class_blocks:
            output_path = target_dir / f"{class_name}.java"
            output_path.write_text(code, encoding="utf-8")
            written.append(output_path)
        else:
            for detected_class, block in class_blocks.items():
                output_path = target_dir / f"{detected_class}.java"
                prefix = imports + "\n\n" if imports else ""
                output_path.write_text(prefix + block.strip() + "\n", encoding="utf-8")
                written.append(output_path)

        report_path = target_dir / "migration-report.md"
        report_path.write_text(service.migration_report(run_id, file_id), encoding="utf-8")
        written.append(report_path)
        return written

    def _split_classes(self, code: str) -> dict[str, str]:
        blocks = {}
        for match in self.CLASS_RE.finditer(code):
            name = match.group(1)
            brace_index = code.find("{", match.end())
            if brace_index == -1:
                continue
            end_index = self._matching_brace(code, brace_index)
            if end_index == -1:
                continue
            blocks[name] = code[match.start():end_index + 1]
        return blocks

    @staticmethod
    def _matching_brace(code: str, open_index: int) -> int:
        depth = 0
        for index in range(open_index, len(code)):
            char = code[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return index
        return -1
