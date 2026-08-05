from pathlib import Path
import re
p = Path(__file__).resolve().parent / 'src' / 'services' / 'api.ts'
text = p.read_text(encoding='utf-8')
pattern = re.compile(r"^[ \t]*config\.headers\.Authorization.*$", flags=re.MULTILINE)
if not pattern.search(text):
    print('Could not find config.headers.Authorization line. Context:')
    idx = text.find('config.headers.Authorization')
    print(text[idx-120:idx+120])
else:
    replacement = "config.headers = config.headers || {};\n    config.headers.Authorization = `Bearer ${token}`;"
    new_text = pattern.sub(replacement, text, count=1)
    backup = p.with_suffix('.ts.bak')
    backup.write_text(text, encoding='utf-8')
    p.write_text(new_text, encoding='utf-8')
    print('Patched file and wrote backup to', backup)
