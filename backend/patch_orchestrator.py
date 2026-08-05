import re
from pathlib import Path
p = Path(__file__).resolve().parent / 'Agents' / 'implementations' / 'agentic_code_conversion_orchestrator.py'
bak = p.with_suffix('.py.bak')
text = p.read_text(encoding='utf-8')
# Backup
bak.write_text(text, encoding='utf-8')
pattern = re.compile(r"\n[ \t]*if api_key:.*\r?\n")
if not pattern.search(text):
    print('Pattern not found; aborting.')
    raise SystemExit(1)
replacement = '''
        # Use provided API key when available (OpenAI-compatible services expect 'Authorization: Bearer <key>').
        if api_key:
            key_str = str(api_key).strip()
            if key_str.lower().startswith("bearer "):
                headers["Authorization"] = key_str
            else:
                headers["Authorization"] = f"Bearer {key_str}"
'''
new_text = pattern.sub(replacement, text, count=1)
p.write_text(new_text, encoding='utf-8')
print('Patched file and wrote backup to', bak)
