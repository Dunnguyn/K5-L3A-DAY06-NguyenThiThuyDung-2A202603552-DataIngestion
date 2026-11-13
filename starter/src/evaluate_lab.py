"""Review the provisional dev run, freeze a selection, then retrieve test traces."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .chroma_store import ChromaStore, DEFAULT_PATH
from .embeddings import DEFAULT_MODEL, MyEmbedder
from .evaluation import evaluate_query, evidence_candidate, load_jsonl, summarize
from .run import BENCHMARK, DATA, OUT, write_jsonl

EVAL = Path("starter/results/evaluation")
COLLECTION_PREFIX = 'day06_experiment'


def load_questions(split):
    return {q['id']: q for q in json.loads(BENCHMARK.read_text(encoding='utf-8')) if q['split'] == split}


def label_rows(traces, questions):
    """Conservative review for this benchmark: documented exact gold on gold page.

    The reviewer must inspect same-page near misses and explicitly check whether
    an equivalent complete passage should receive credit before claiming final scores.
    """
    result = []
    for trace in traces:
        question = questions[trace['question_id']]
        labels = [evidence_candidate(question, h) for h in trace['results']]
        score = evaluate_query(question, trace['results'], labels)
        result.append({**trace, **score, "review_method": "exact gold quote and source/page; near misses require review"})
    return result


def dev():
    EVAL.mkdir(parents=True, exist_ok=True)
    if (EVAL / 'selection.json').exists():
        raise SystemExit('Existing selection must be preserved; use a new experiment directory')
    if (EVAL / 'traces_test.jsonl').exists():
        raise SystemExit('Test results already exist; do not reselect using this test set. Use a new, untouched test set for a new experiment.')
    traces = load_jsonl(OUT / 'traces_dev.jsonl')
    if any(t['split'] != 'dev' for t in traces):
        raise ValueError('Expected dev traces only')
    questions = load_questions('dev')
    labelled = label_rows(traces, questions)
    metrics = summarize(labelled)
    write_jsonl(EVAL / 'dev_exact_review.jsonl', labelled)
    (EVAL / 'dev_exact_metrics.json').write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
    # The rule is defined before querying the test set: Hit@3, then Hit@1,
    # then fewer chunks, with alphabetical order as a final stable tie-break.
    stats = json.loads((OUT / 'summary.json').read_text(encoding='utf-8'))
    chunk_counts = {'A': stats['strategies']['A']['chunks'], 'B': stats['strategies']['B']['chunks'], 'C': stats['strategies']['B']['chunks']}
    selected = min('ABC', key=lambda s: (-metrics[s + '_dev']['hit3'], -metrics[s + '_dev']['hit1'], chunk_counts[s], s))
    selection = {'status': 'provisional; exact-quote scores; near misses need human review; corpus not validated',
                 'rule': 'highest dev exact-quote Hit@3, then Hit@1, then fewest chunks, then alphabetical',
                 'selected': selected, 'dev_metrics': metrics, 'chunks': chunk_counts,
                 'data_sha256': hashlib.sha256(DATA.read_bytes()).hexdigest(),
                 'dev_trace_sha256': hashlib.sha256((OUT / 'traces_dev.jsonl').read_bytes()).hexdigest(),
                 'benchmark_sha256': hashlib.sha256(BENCHMARK.read_bytes()).hexdigest(),
                 'selected_at_utc': datetime.now(timezone.utc).isoformat(),
                 'test_traces_examined_at_selection': False}
    (EVAL / 'selection.json').write_text(json.dumps(selection, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(selection, ensure_ascii=False, indent=2))


def test():
    if (EVAL / 'traces_test.jsonl').exists():
        raise SystemExit('Existing test traces must be preserved; use a new experiment directory')
    selection = json.loads((EVAL / 'selection.json').read_text(encoding='utf-8'))
    for path, field in ((DATA, 'data_sha256'), (BENCHMARK, 'benchmark_sha256'), (OUT / 'traces_dev.jsonl', 'dev_trace_sha256')):
        if hashlib.sha256(path.read_bytes()).hexdigest() != selection[field]:
            raise SystemExit(f"{path} changed since selection; reselect before running test")
    questions = load_questions('test')
    if len(questions) < 5:
        raise SystemExit('Expected at least five test questions')
    model = MyEmbedder(DEFAULT_MODEL)
    if any(len(model.model.tokenizer.encode(q['question'], add_special_tokens=True, truncation=False)) > model.model.max_seq_length for q in questions.values()):
        raise SystemExit('A test question exceeds the model token limit')
    stores = {s: ChromaStore(DEFAULT_PATH, f'{COLLECTION_PREFIX}_{s.lower()}', DEFAULT_MODEL, model.dimensions) for s in 'AB'}
    for s, store in stores.items():
        if store.collection.count() != selection['chunks'][s]:
            raise SystemExit(f'Collection {s} changed since selection')
    vectors = model.embed_documents([q['question'] for q in questions.values()])
    traces = []
    for q, vector in zip(questions.values(), vectors):
        for strategy in 'ABC':
            filt = q.get('filter') if strategy == 'C' else None
            if filt and set(filt) != {'section'}:
                raise ValueError('Only section filters are supported')
            start = time.perf_counter()
            hits = stores['A' if strategy == 'A' else 'B'].search(vector, 3, filt.get('section') if filt else None)
            traces.append({'strategy': strategy, 'question_id': q['id'], 'split': 'test', 'question': q['question'],
                           'filter_applied': filt, 'gold_source_id': q['gold_source_id'], 'gold_page': q['gold_page'],
                           'evidence_quote': q['evidence_quote'], 'search_seconds': round(time.perf_counter() - start, 5), 'results': hits})
    write_jsonl(EVAL / 'traces_test.jsonl', traces)
    labelled = label_rows(traces, questions)
    write_jsonl(EVAL / 'test_exact_review.jsonl', labelled)
    (EVAL / 'test_exact_metrics.json').write_text(json.dumps(summarize(labelled), indent=2) + '\n', encoding='utf-8')
    print(f"Saved {len(traces)} test traces, using frozen provisional selection {selection['selected']}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('dev', 'test'))
    args = parser.parse_args()
    (dev if args.phase == 'dev' else test)()
