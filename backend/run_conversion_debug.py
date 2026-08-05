import json, traceback
from pathlib import Path
import sys
backend_root = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_root))
from Agents.implementations.agentic_code_conversion_orchestrator import AgenticCodeConversionOrchestrator

llm_config = {"mode": "local", "url": "http://127.0.0.1:11434", "model": "llama3", "timeout": 120}
orc = AgenticCodeConversionOrchestrator(llm_config)

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

try:
    print('Calling _convert_with_agent...')
    res = orc._convert_with_agent(context=context, agent_key='generic', project_id='default')
    print('Response:')
    print(json.dumps(res, indent=2))
except Exception as e:
    print('Exception during _convert_with_agent:')
    traceback.print_exc()
