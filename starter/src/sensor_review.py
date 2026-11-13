"""Store the assistant's provisional review of the sensor experiment."""
from pathlib import Path
import json
from pypdf import PdfReader
from .ingestion import normalize_text
from .run import read_jsonl, write_jsonl

ROOT = Path('starter/results/sensor_run')

def main():
    pages = read_jsonl(Path('starter/data/sensor_pages.jsonl'))
    pdf = PdfReader('starter/data/documents.pdf')
    chunks = {s: read_jsonl(ROOT / 'dev' / f'chunks_{s.lower()}.jsonl') for s in 'AB'}
    sampled = pages[:10]
    coherence = []
    for page in sampled:
        for strategy in 'ABC':
            group = 'A' if strategy == 'A' else 'B'
            chunk = next(c for c in chunks[group] if c['page'] == page['page'] and c['metadata']['start_char'] == 0)
            cut = page['page'] == 24 and group == 'A'
            coherence.append({'strategy': strategy, 'page': page['page'], 'position': 0,
                              'chunk_id': chunk['chunk_id'], 'text': chunk['text'],
                              'score': 1 if cut else 2,
                              'reason': 'Kết thúc giữa câu cuối' if cut else 'Giữ được tiêu đề và các ý của phần được lấy',
                              'reviewer': 'Codex; cần học viên kiểm tra lại'})
    traces = read_jsonl(ROOT / 'evaluation' / 'traces_test.jsonl')
    scores = {'SQ16': {'A':2,'B':2,'C':2}, 'SQ17': {'A':1,'B':2,'C':2},
              'SQ18': {'A':2,'B':2,'C':2}, 'SQ19': {'A':2,'B':2,'C':2},
              'SQ20': {'A':0,'B':0,'C':2}}
    reasons = {'SQ16':'Có đoạn giải thích mục đích lọc nhiễu.',
               'SQ17':'ADC được mô tả; riêng A cắt giữa câu định nghĩa, B/C có đầy đủ trong một chunk.',
               'SQ18':'Có đủ ba bước lấy mẫu, lượng tử hóa và mã hóa.',
               'SQ19':'Có các loại dữ liệu cần loại bỏ khi lọc.',
               'SQ20':'A/B không truy xuất được định nghĩa chuẩn hóa ở trang 47; C tìm thấy trong top 3.'}
    grounding, metadata = [], []
    for t in traces:
        grounding.append({'question_id':t['question_id'],'strategy':t['strategy'],
                          'score':scores[t['question_id']][t['strategy']], 'reason':reasons[t['question_id']],
                          'reviewer':'Codex; cần học viên kiểm tra lại'})
        for rank,h in enumerate(t['results'],1):
            m=h['metadata']; original=next(p for p in pages if p['page']==m['page'])
            raw=normalize_text(pdf.pages[m['page']-1].extract_text() or '')
            section=(t.get('filter_applied') or {}).get('section')
            valid=(m.get('document_id')=='SENSOR001' and m.get('source')==original['source']
                   and raw==original['text'] and m.get('section')==original['metadata']['section']
                   and h['text']==raw[m['start_char']:m['end_char']])
            metadata.append({'question_id':t['question_id'],'strategy':t['strategy'],'rank':rank,
                             'chunk_id':h['chunk_id'],'source_page_text_section_match':valid,
                             'filter_compliant':m.get('section')==section if section else None,
                             'basis':'so sánh văn bản, offset, trang với PDF và section được gán theo phạm vi trang; cần người học xác nhận'})
    dest=ROOT/'evaluation'
    write_jsonl(dest/'coherence_review.jsonl',coherence)
    write_jsonl(dest/'grounding_review.jsonl',grounding)
    write_jsonl(dest/'metadata_audit.jsonl',metadata)
    summary={}
    for s in 'ABC':
        c=[x for x in coherence if x['strategy']==s]; g=[x for x in grounding if x['strategy']==s]
        m=[x for x in metadata if x['strategy']==s]; filtered=[x for x in traces if x['strategy']==s and x['filter_applied']]
        summary[s]={'coherence_mean':sum(x['score'] for x in c)/len(c),'coherence_n':len(c),
                    'grounding_mean':sum(x['score'] for x in g)/len(g),
                    'grounding_0_1_2':[sum(x['score']==i for x in g) for i in range(3)],
                    'metadata_correct':sum(x['source_page_text_section_match'] for x in m),'metadata_n':len(m),
                    'filter_questions_ok':sum(all(h['metadata'].get('section')==x['filter_applied']['section'] for h in x['results']) for x in filtered),
                    'filter_questions_n':len(filtered)}
    (dest/'review_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
