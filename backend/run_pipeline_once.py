import json
import sys
from pathlib import Path

from Persistence.sqlite.session import SessionLocal
from Processes.full_code_generation_pipeline import FullCodeGenerationPipeline


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python run_pipeline_once.py RUN_ID TARGET_LANGUAGE [OUTPUT_JSON]")
        return 2

    run_id = sys.argv[1]
    target_language = sys.argv[2]
    output_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    db = SessionLocal()
    try:
        result = FullCodeGenerationPipeline(db).run(
            run_id=run_id,
            target_language=target_language,
            project_id=run_id,
        )
    finally:
        db.close()

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
