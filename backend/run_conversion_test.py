import json
import sys
from pathlib import Path

# Ensure backend package is importable
backend_root = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_root))

try:
    from Agents.implementations.agentic_code_conversion_orchestrator import AgenticCodeConversionOrchestrator
except Exception as e:
    print("Failed to import orchestrator:", e)
    raise

# Configure a local LLM (Ollama-like) — adjust URL/model if needed
llm_config = {
    "mode": "local",
    "url": "http://127.0.0.1:11434",
    "model": "llama3",
    "timeout": 120,
}

orc = AgenticCodeConversionOrchestrator(llm_config)

# Small sample COBOL program (very simple) to convert to Python for testing
sample_cobol = '''
       IDENTIFICATION DIVISION.
       PROGRAM-ID. HELLO.
       PROCEDURE DIVISION.
           DISPLAY "Hello, world".
           STOP RUN.
'''

context = {
    "source_language": "cobol",
    "target_language": "python",
    "file_name": "HELLO",
    "file_id": "hello-001",
    "source_code": sample_cobol,
    "conversion_plan": {"steps": ["translate_display_to_print", "map_stop_run_to_exit"]},
    "technical_yaml": "",
    "business_rules": {},
    "procedural_flow": {},
    "dependencies": {},
    "locked_symbols": [],
}

print("Running conversion test with local LLM config:", llm_config)

try:
    result = orc.convert(context)
    print("\n--- Conversion Result ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print("Conversion failed:", repr(e))
    raise
