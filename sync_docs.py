import os, requests
from pathlib import Path

SB_URL = os.environ['SUPABASE_URL']
SB_KEY = os.environ['SUPABASE_KEY']
H = {
    'apikey': SB_KEY,
    'Authorization': 'Bearer ' + SB_KEY,
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates'
}

def read(f):
    n = f.name.lower()
    try:
        if n.endswith('.docx') or n.endswith('.doc'):
            from docx import Document
            return chr(10).join(p.text for p in Document(f).paragraphs if p.text.strip())
        if n.endswith('.pdf'):
            import PyPDF2
            with open(f, 'rb') as fp:
                return chr(10).join(p.extract_text() or '' for p in PyPDF2.PdfReader(fp).pages)
        if n.endswith(('.txt', '.md', '.json')):
            return f.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print('  error:', e)
    return ''

done = 0
for f in sorted(Path('docs').iterdir()):
    if not f.is_file() or f.name in ('README.md', 'example.txt'):
        continue
    print('Processing:', f.name)
    text = read(f)
    if not text or len(text.strip()) < 20:
        print('  skipped')
        continue
    r = requests.post(SB_URL + '/rest/v1/docs_index', headers=H,
                      json={'filename': f.name, 'content': text})
    print('  OK' if r.status_code in (200, 201) else '  ERR ' + str(r.status_code))
    if r.status_code in (200, 201):
        done += 1

print('Done:', done, 'files synced')
