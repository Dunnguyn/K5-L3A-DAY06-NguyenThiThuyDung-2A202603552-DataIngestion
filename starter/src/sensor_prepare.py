"""Extract selected content pages from the instructor-supplied sensor PDF."""
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader
from .ingestion import normalize_text

PAGES = [5, 14] + list(range(19, 35)) + list(range(36, 49))

def main():
    if Path('starter/data/sensor_pages.jsonl').exists():
        raise SystemExit('Existing parsed corpus found; preserve it before preparing a new experiment version.')
    source = Path('starter/data/documents.pdf')
    manifest = json.loads(Path('data/manifest.json').read_text(encoding='utf-8'))
    expected = next(d['sha256'] for d in manifest['documents'] if d['source_id'] == 'SENSOR001')
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise SystemExit('PDF differs from the manifest; verify the source and update the corpus before running.')
    pdf = PdfReader(source)
    if len(pdf.pages) != 49:
        raise SystemExit('Expected the 49-page sensor lecture PDF. Check the file before continuing.')
    rows = []
    for n in PAGES:
        section = ('2.1 Cảm biến và cơ cấu chấp hành' if n <= 31 else
                   '2.2 Khuếch đại, lọc và xử lý tín hiệu' if n <= 34 else
                   '2.3 Chuyển đổi ADC, DAC' if n <= 39 else
                   '2.4 Thu thập và xử lý dữ liệu cảm biến' if n <= 46 else
                   '2.5 Các giải thuật xử lý dữ liệu')
        text = normalize_text(pdf.pages[n-1].extract_text() or '')
        if not text:
            raise SystemExit(f'No extractable text on page {n}')
        rows.append({'document_id':'SENSOR001','source':str(source).replace('\\','/'),
                     'page':n,'text':text,'metadata':{'section':section}})
    out = Path('starter/data/sensor_pages.jsonl')
    out.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
    print(f'{len(rows)} pages -> {out}')

if __name__ == '__main__':
    main()
