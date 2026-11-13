"""Prepare strategies A/B/C and run the dev retrieval experiment.

The test split is intentionally not queried here. Results remain provisional
until the source corpus, its valid-page count and its permissions are audited.
Run from the project root with: python -m starter.src.run
"""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
import time
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from .chroma_store import ChromaStore, DEFAULT_PATH
from .chunking import _chunk
from .embeddings import DEFAULT_MODEL, MyEmbedder
from .models import DocumentPage
from .token_chunking import token_bounded

DATA = Path("starter/data/parsed_pages.jsonl")
BENCHMARK = Path("starter/benchmark/questions.json")
OUT = Path("starter/results/experiment_dev")
COLLECTION_PREFIX = "day06_experiment"
LOG_PATH = Path("artifacts/experiment_log.csv")


def fixed_token_safe(page, tokenizer, max_tokens, size=500, overlap=50):
    """Fixed character windows, shortened only if the model token limit requires it."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("invalid fixed window size or overlap")
    result, start = [], 0
    while start < len(page.text):
        end = min(start + size, len(page.text))
        while len(tokenizer.encode(page.text[start:end], add_special_tokens=True, truncation=False)) > max_tokens:
            end -= 1
            if end <= start:
                raise ValueError("Token limit too small for a character")
        result.append(_chunk(page, "fixed_tokens", start, end))
        if end == len(page.text):
            break
        start = max(start + 1, end - overlap)
    return result


def read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    if (OUT / "traces_dev.jsonl").exists() or LOG_PATH.exists():
        raise SystemExit("Existing run or log found; choose a new versioned output and log path to preserve history")
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [DocumentPage(**row) for row in read_jsonl(DATA)]
    if not pages:
        raise SystemExit("No parsed pages; complete ingestion first")
    # Load only dev entries for retrieval; the test set remains untouched.
    questions = [q for q in json.loads(BENCHMARK.read_text(encoding="utf-8")) if q["split"] == "dev"]
    if len(questions) < 15 or len({q['id'] for q in questions}) != len(questions):
        raise SystemExit("Expected at least 15 distinct dev questions")
    model_started = time.perf_counter()
    embedder = MyEmbedder(DEFAULT_MODEL)
    model_load_seconds = time.perf_counter() - model_started
    tokenizer, limit = embedder.model.tokenizer, embedder.model.max_seq_length
    model_revision = getattr(embedder.model[0].auto_model.config, "_commit_hash", None)
    if any(len(tokenizer.encode(q['question'], add_special_tokens=True, truncation=False)) > limit for q in questions):
        raise SystemExit("A dev question exceeds the model token limit")

    datasets, stats = {}, {}
    for key in ("A", "B"):
        begin = time.perf_counter()
        groups = [(fixed_token_safe(p, tokenizer, limit) if key == "A" else token_bounded(p, tokenizer, limit)) for p in pages]
        chunks = [c for group in groups for c in group]
        # Ensure every original input character is covered by the windows.
        for page, group in zip(pages, groups):
            if page.text and (not group or group[0].metadata['start_char'] != 0 or group[-1].metadata['end_char'] != len(page.text)):
                raise RuntimeError(f"Incomplete coverage: {key} page {page.page}")
            if any(a.metadata['end_char'] < b.metadata['start_char'] for a, b in zip(group, group[1:])):
                raise RuntimeError(f"Gap in chunks: {key} page {page.page}")
        chunk_time = time.perf_counter() - begin
        token_lengths = [len(tokenizer.encode(c.text, add_special_tokens=True, truncation=False)) for c in chunks]
        if not chunks or max(token_lengths) > limit:
            raise RuntimeError(f"Invalid token limit for strategy {key}")
        begin = time.perf_counter()
        vectors = embedder.embed_documents([c.text for c in chunks])
        embed_time = time.perf_counter() - begin
        if len(chunks) != len(vectors):
            raise RuntimeError("Chunk/vector count mismatch")
        rows = [{**asdict(c), "embedding": v} for c, v in zip(chunks, vectors)]
        store = ChromaStore(DEFAULT_PATH, f"{COLLECTION_PREFIX}_{key.lower()}", DEFAULT_MODEL, embedder.dimensions)
        begin = time.perf_counter()
        stored, stale = store.sync(rows)
        store_time = time.perf_counter() - begin
        if stored != len(rows):
            raise RuntimeError("Unexpected collection count")
        write_jsonl(OUT / f"chunks_{key.lower()}.jsonl", [asdict(c) for c in chunks])
        lengths = [len(c.text) for c in chunks]
        stats[key] = {"chunks": len(chunks), "characters_total": sum(lengths),
                      "chars_min": min(lengths), "chars_mean": round(statistics.mean(lengths), 2), "chars_max": max(lengths),
                      "tokens_min": min(token_lengths), "tokens_mean": round(statistics.mean(token_lengths), 2),
                      "tokens_max": max(token_lengths), "tokens_over_limit": 0,
                      "chunk_seconds": round(chunk_time, 3), "embedding_seconds": round(embed_time, 3),
                      "store_seconds": round(store_time, 3), "removed_stale": stale}
        datasets[key] = store

    query_start = time.perf_counter()
    query_vectors = embedder.embed_documents([q['question'] for q in questions])
    query_embedding_seconds = time.perf_counter() - query_start
    traces = []
    search_times = {k: 0.0 for k in ("A", "B", "C")}
    for q, query_vector in zip(questions, query_vectors):
        for strategy in ("A", "B", "C"):
            metadata_filter = q.get("filter") if strategy == "C" else None
            if metadata_filter and set(metadata_filter) != {"section"}:
                raise ValueError("This experiment supports section filters only")
            begin = time.perf_counter()
            hits = datasets["A" if strategy == "A" else "B"].search(
                query_vector, top_k=3, section=metadata_filter.get("section") if metadata_filter else None)
            elapsed = time.perf_counter() - begin
            search_times[strategy] += elapsed
            traces.append({"strategy": strategy, "question_id": q["id"], "split": "dev",
                           "question": q["question"], "filter_applied": metadata_filter,
                           "gold_source_id": q["gold_source_id"], "gold_page": q["gold_page"],
                           "evidence_quote": q["evidence_quote"], "search_seconds": round(elapsed, 5),
                           "results": hits})
    write_jsonl(OUT / "traces_dev.jsonl", traces)
    summary = {"status": "provisional: corpus page validity and license not verified",
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "source_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
               "model": DEFAULT_MODEL, "model_revision": model_revision,
               "sentence_transformers_version": version("sentence-transformers"),
               "chromadb_version": version("chromadb"), "dimensions": embedder.dimensions,
               "max_sequence_tokens": limit, "model_load_seconds": round(model_load_seconds, 3),
               "dev_questions": len(questions), "test_queried": False,
               "query_embedding_seconds": round(query_embedding_seconds, 3),
               "search_seconds": {k: round(v, 3) for k, v in search_times.items()},
               "cost": "0 local inference; electricity not measured", "strategies": stats}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["strategy", "chunking", "chunk_size", "overlap", "metadata", "filter", "vectorizer", "hypothesis",
              "dev_hit1", "dev_hit3", "test_hit1", "test_hit3", "notes"]
    descriptions = {
        "A": ("fixed characters, shortened to fit token limit", "max 500 characters; max 128 tokens", "up to 50 characters", "none", "Fixed windows provide a baseline."),
        "B": ("paragraph/sentence, token safe", "max 800 characters; max 128 tokens", "0", "none", "Structure-aware chunks may preserve context better."),
        "C": ("same chunks as B", "same as B", "0", "question section when supplied", "Section filtering may improve retrieval for scoped questions."),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for strategy, (chunking, size, overlap, filt, hypothesis) in descriptions.items():
            writer.writerow(dict(strategy=strategy, chunking=chunking, chunk_size=size, overlap=overlap,
                                 metadata="document_id, source, page, section when known", filter=filt,
                                 vectorizer=DEFAULT_MODEL, hypothesis=hypothesis,
                                 notes=f"Provisional corpus; manual evidence scoring pending; see {OUT / 'summary.json'}"))
    print(f"Completed {len(traces)} dev traces; test not queried. See {OUT / 'summary.json'}")


if __name__ == "__main__":
    main()
