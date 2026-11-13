"""Record the assistant's explicit, provisional manual review of this run."""
import csv
import json
from pathlib import Path

from .evaluate_lab import EVAL
from .evaluation import load_jsonl
from .run import DATA, OUT, write_jsonl


def main():
    pages = load_jsonl(DATA)
    by_strategy = {s: load_jsonl(OUT / f'chunks_{s.lower()}.jsonl') for s in 'AB'}
    # Predeclared positions: physical PDF pages 3–12, offset 100 in the
    # first extracted segment of each page. C uses exactly B's chunks.
    reasons = {
        'A': ['Complete purpose, next sentence cut', 'Complete opening, next sentence cut',
              'Starts mid-sentence and ends mid-sentence', 'Starts mid-sentence; ending cut',
              'Starts mid-sentence and citation cut', 'Main idea complete, next sentence cut',
              'Starts in a citation, main idea complete', 'Starts mid-sentence; ending cut',
              'Starts mid-sentence; missing earlier context', 'Main idea complete, next sentence cut'],
        'B': ['Title and complete purpose', 'Complete introduction sentences',
              'Starts mid-sentence from preceding page', 'Starts mid-sentence from preceding page',
              'Starts mid-sentence from preceding page', 'Complete heading and sentences',
              'Starts in a citation, main idea complete', 'Starts mid-sentence from preceding page',
              'Starts mid-sentence; missing earlier context', 'Complete sentences on empathy and participation'],
    }
    scores = {'A': [1,1,1,1,1,1,1,1,1,1], 'B': [2,2,1,1,1,2,1,1,1,2]}
    coherence = []
    for page_number in range(3, 13):
        page = next(p for p in pages if p['page'] == page_number)
        pos = min(100, len(page['text']) - 1)
        for strategy in 'ABC':
            group = 'A' if strategy == 'A' else 'B'
            chunk = next(c for c in by_strategy[group] if c['page'] == page_number
                         and c['metadata'].get('section') == page['metadata'].get('section')
                         and c['metadata']['start_char'] <= pos < c['metadata']['end_char']
                         and c['text'] == page['text'][c['metadata']['start_char']:c['metadata']['end_char']])
            coherence.append({'strategy': strategy, 'page': page_number, 'segment_offset': pos,
                              'chunk_id': chunk['chunk_id'], 'text': chunk['text'],
                              'score': scores[group][page_number - 3], 'reason': reasons[group][page_number - 3],
                              'reviewer': 'Codex assistant; provisional and not independent'})
    write_jsonl(EVAL / 'coherence_review.jsonl', coherence)

    notes = {
        'Q16': {'A': (1, 'Visual approaches discussed, but neither design probes nor games identified.'),
                'B': (2, 'Top 1 explicitly identifies design probes and games.'), 'C': (2, 'Same evidence as B.')},
        'Q17': {s: (2, 'Top 1 covers framing, participatory envisioning, and iterative testing.') for s in 'ABC'},
        'Q18': {'A': (1, 'Top 2 lists clinical, self-reported, and wellness data but cuts off before social determinants.'),
                'B': (2, 'Top 2 lists all requested data sources and social determinants.'), 'C': (2, 'Same complete evidence as B.')},
        'Q19': {'A': (1, 'Top 1 states the objective on page 21, but does not retrieve the requested Table 1 on page 41.'),
                'B': (0, 'No retrieved passage states the requested objective in Table 1.'),
                'C': (0, 'No retrieved passage states the requested objective in Table 1.')},
        'Q20': {s: (2, 'Top 1 gives 30 to 26 pages, shorter sections, and reduced repetition.') for s in 'ABC'},
    }
    traces = load_jsonl(EVAL / 'traces_test.jsonl')
    grounding, audit = [], []
    for trace in traces:
        question, strategy = trace['question_id'], trace['strategy']
        score, reason = notes[question][strategy]
        grounding.append({'question_id': question, 'strategy': strategy, 'score': score, 'reason': reason,
                          'reviewer': 'Codex assistant; provisional and not independent'})
        for rank, hit in enumerate(trace['results'], 1):
            meta = hit['metadata']
            matches = [p for p in pages if p['document_id'] == meta.get('document_id')
                       and p['page'] == meta.get('page') and p['source'] == meta.get('source')
                       and p['metadata'].get('section') == meta.get('section')
                       and hit['text'] == p['text'][meta['start_char']:meta['end_char']]]
            requested = (trace.get('filter_applied') or {}).get('section')
            audit.append({'question_id': question, 'strategy': strategy, 'rank': rank, 'chunk_id': hit['chunk_id'],
                          'source_page_section_match': bool(matches),
                          'filter_compliant': (meta.get('section') == requested) if requested else None,
                          'basis': 'Exact match to extracted source segment and offsets; source PDF content spot-checked',
                          'reviewer': 'Codex assistant; provisional and not independent'})
    write_jsonl(EVAL / 'grounding_review.jsonl', grounding)
    write_jsonl(EVAL / 'metadata_audit.jsonl', audit)
    summary = {}
    for strategy in 'ABC':
        cr = [r for r in coherence if r['strategy'] == strategy]
        gr = [r for r in grounding if r['strategy'] == strategy]
        ar = [r for r in audit if r['strategy'] == strategy]
        filtered = [t for t in traces if t['strategy'] == strategy and t.get('filter_applied')]
        summary[strategy] = {'coherence_mean': sum(r['score'] for r in cr) / len(cr), 'coherence_n': len(cr),
                             'grounding_mean': sum(r['score'] for r in gr) / len(gr),
                             'grounding_score_counts': {str(i): sum(r['score'] == i for r in gr) for i in range(3)},
                             'metadata_correct': sum(r['source_page_section_match'] for r in ar), 'metadata_total': len(ar),
                             'filtered_queries_compliant': sum(all(h['metadata'].get('section') == t['filter_applied']['section'] for h in t['results']) for t in filtered),
                             'filtered_queries_total': len(filtered)}
    (EVAL / 'manual_review_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
