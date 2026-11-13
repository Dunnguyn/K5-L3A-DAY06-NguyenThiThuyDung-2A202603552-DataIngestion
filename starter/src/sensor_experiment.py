"""Run sensor corpus experiments without overwriting the earlier experiment."""
import argparse
from pathlib import Path

from . import evaluate_lab, run

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'retrieve-dev', 'select-dev', 'retrieve-test'))
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    BASE = args.output_dir.resolve()
    if args.phase == 'prepare':
        from .sensor_prepare import prepare
        try:
            BASE.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            parser.error("Choose a new output directory for prepare")
        try:
            prepare(BASE / 'pages.jsonl')
        except Exception as exc:
            (BASE / 'ingestion_error.log').write_text(str(exc), encoding='utf-8')
            raise
        raise SystemExit(0)
    if not (BASE / 'pages.jsonl').is_file():
        parser.error('Run prepare in a new output directory first')
    run.DEFAULT_PATH = evaluate_lab.DEFAULT_PATH = str(BASE / 'chroma')
    run.DATA = BASE / 'pages.jsonl'
    run.BENCHMARK = Path('starter/benchmark/sensor_questions.json')
    run.OUT = BASE / 'dev'
    run.LOG_PATH = BASE / 'experiment_log.csv'
    run.COLLECTION_PREFIX = 'day06_sensor'
    evaluate_lab.DATA = run.DATA
    evaluate_lab.BENCHMARK = run.BENCHMARK
    evaluate_lab.OUT = run.OUT
    evaluate_lab.EVAL = BASE / 'evaluation'
    evaluate_lab.COLLECTION_PREFIX = run.COLLECTION_PREFIX

    if args.phase == 'retrieve-dev':
        if (run.OUT / 'traces_dev.jsonl').exists() or (evaluate_lab.EVAL / 'selection.json').exists():
            raise SystemExit('Existing experiment found; preserve its history and use a new versioned output directory.')
        if (evaluate_lab.EVAL / 'traces_test.jsonl').exists():
            raise SystemExit('Test already viewed; use a fresh experiment directory and new test set.')
        run.main()
    elif args.phase == 'select-dev':
        if (evaluate_lab.EVAL / 'selection.json').exists():
            raise SystemExit('Existing selection found; preserve it and use a new versioned output directory.')
        evaluate_lab.dev()
    else:
        if (evaluate_lab.EVAL / 'traces_test.jsonl').exists():
            raise SystemExit('Existing test traces found; preserve them and use a new versioned output directory.')
        evaluate_lab.test()
