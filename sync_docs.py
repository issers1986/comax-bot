import os, requests, zipfile
from pathlib import Path

SB_URL = os.environ['SUPABASE_URL']
SB_KEY = os.environ['SUPABASE_KEY']
H = {
    'apikey': SB_KEY,
    'Authorization': 'Bearer ' + SB_KEY,
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates'
}

def upload_image(img_bytes, filename, mime='image/png'):
    r = requests.post(
        SB_URL + '/storage/v1/object/doc-images/' + filename,
        headers={'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY, 'Content-Type': mime, 'x-upsert': 'true'},
        data=img_bytes
    )
    if r.status_code in (200, 201):
        return SB_URL + '/storage/v1/object/public/doc-images/' + filename
    return None

def read(f):
    n = f.name.lower()
    try:
        if n.endswith('.docx') or n.endswith('.doc'):
            from docx import Document
            doc = Document(f)
            text = chr(10).join(p.text for p in doc.paragraphs if p.text.strip())
            img_urls = []
            # קרא תמונות ישירות מה-zip
            with zipfile.ZipFile(f) as z:
                media_files = [m for m in z.namelist() if m.startswith('word/media/')]
                for media_path in media_files:
                    try:
                        ext = media_path.split('.')[-1].lower()
                        mime = 'image/jpeg' if ext in ('jpg','jpeg') else 'image/' + ext
                        img_data = z.read(media_path)
                        img_name = f.stem + '_' + media_path.split('/')[-1]
                        url = upload_image(img_data, img_name, mime)
                        if url:
                            img_urls.append(url)
                            print('  image:', img_name)
                    except Exception as e:
                        print('  img error:', e)
            if img_urls:
                text += chr(10) + chr(10) + 'תמונות:' + chr(10) + chr(10).join(img_urls)
            return text

        if n.endswith('.pdf'):
            try:
                import fitz
                pdf = fitz.open(f)
                text = ''
                img_urls = []
                for page_num, page in enumerate(pdf):
                    text += page.get_text() + chr(10)
                    for img_idx, img in enumerate(page.get_images()):
                        try:
                            xref = img[0]
                            base_img = pdf.extract_image(xref)
                            img_bytes = base_img['image']
                            ext = base_img['ext']
                            img_name = f.stem + '_p' + str(page_num) + '_' + str(img_idx) + '.' + ext
                            url = upload_image(img_bytes, img_name, 'image/' + ext)
                            if url:
                                img_urls.append(url)
                                print('  image:', img_name)
                        except: pass
                if img_urls:
                    text += chr(10) + chr(10) + 'תמונות:' + chr(10) + chr(10).join(img_urls)
                return text
            except:
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
