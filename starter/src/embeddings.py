"""Create real, normalized sentence-transformer embeddings for chunks and queries."""

from __future__ import annotations

import argparse
import json
import math
import time
from importlib.metadata import version
from pathlib import Path
from typing import Protocol

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Candidate observed in the local cache; the historical run did not record its revision.
DEFAULT_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, question: str) -> list[float]: ...


class MyEmbedder:
    """Local Sentence Transformers adapter, shared by documents and queries."""

    def __init__(self, model_name: str = DEFAULT_MODEL, batch_size: int = 16) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install sentence-transformers in the active environment first") from exc
        self.model_name = model_name
        self.batch_size = batch_size
        self.revision = DEFAULT_REVISION if model_name == DEFAULT_MODEL else None
        self.model = SentenceTransformer(model_name, revision=self.revision)
        self.dimensions = self.model.get_sentence_embedding_dimension()
        if not self.dimensions:
            raise ValueError("The selected model did not report an embedding dimension")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(texts, batch_size=self.batch_size,
                                    normalize_embeddings=True, show_progress_bar=True)
        return vectors.tolist()

    def embed_query(self, question: str) -> list[float]:
        if not question.strip():
            raise ValueError("question must not be empty")
        return self.embed_documents([question])[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate embeddings for a chunk JSONL file")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise SystemExit("Input and output paths must differ")
    with args.input.open(encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]
    if not chunks or any(not isinstance(c.get("text"), str) or not c["text"].strip() or not c.get("chunk_id") for c in chunks):
        raise SystemExit("Input must contain non-empty chunks with chunk_id and text")
    ids = [c["chunk_id"] for c in chunks]
    if len(set(ids)) != len(ids):
        raise SystemExit("Duplicate chunk IDs in input")
    started = time.perf_counter()
    embedder = MyEmbedder(args.model, args.batch_size)
    texts = [c["text"] for c in chunks]
    # Count tokenized lengths without truncation to expose model input limits.
    tokenizer = embedder.model.tokenizer
    limit = embedder.model.max_seq_length
    truncated = sum(len(tokenizer.encode(t, add_special_tokens=True, truncation=False)) > limit for t in texts)
    vectors = embedder.embed_documents(texts)
    if len(vectors) != len(chunks) or any(len(v) != embedder.dimensions or not all(math.isfinite(x) for x in v) for v in vectors):
        raise RuntimeError("Embedding count, dimensions, or values are invalid")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for chunk, vector in zip(chunks, vectors):
            output.write(json.dumps({**chunk, "embedding": vector}, ensure_ascii=False) + "\n")
    report = {"model": args.model, "model_revision": embedder.revision, "sentence_transformers_version": version("sentence-transformers"),
              "dimensions": embedder.dimensions, "normalized": True, "batch_size": args.batch_size,
              "chunks": len(chunks), "max_sequence_tokens": limit,
              "chunks_exceeding_token_limit": truncated,
              "elapsed_seconds_including_model_load": round(time.perf_counter() - started, 2)}
    report_path = args.output.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Vectors: {args.output}; report: {report_path}")


if __name__ == "__main__":
    main()
