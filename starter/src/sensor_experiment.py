"""Run sensor corpus experiments without overwriting the earlier experiment."""
import argparse
from pathlib import Path

from . import evaluate_lab, run

BASE = Path('starter/results/sensor_run')
run.DATA = Path('starter/data/sensor_pages.jsonl')
run.BENCHMARK = Path('starter/benchmark/sensor_questions.json')
run.OUT = BASE / 'dev'
run.LOG_PATH = BASE / 'experiment_log.csv'
run.COLLECTION_PREFIX = 'day06_sensor'
evaluate_lab.DATA = run.DATA
evaluate_lab.BENCHMARK = run.BENCHMARK
evaluate_lab.OUT = run.OUT
evaluate_lab.EVAL = BASE / 'evaluation'
evaluate_lab.COLLECTION_PREFIX = run.COLLECTION_PREFIX

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('retrieve-dev', 'select-dev', 'retrieve-test'))
    args = parser.parse_args()
    if args.phase == 'retrieve-dev':
        if (evaluate_lab.EVAL / 'traces_test.jsonl').exists():
            raise SystemExit('Test already viewed; use a fresh experiment directory and new test set.')
        run.main()
    elif args.phase == 'select-dev':
        evaluate_lab.dev()
    else:
        evaluate_lab.test()
