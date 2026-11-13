"""Persist a complete embedding snapshot and search it with cosine distance."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .embeddings import DEFAULT_MODEL, MyEmbedder

DEFAULT_PATH = "starter/storage/chroma"
DEFAULT_COLLECTION = "day06_paragraph_b"


class ChromaStore:
    def __init__(self, path: str, collection: str, model: str, dimensions: int):
        import chromadb

        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine", "embedding_model": model, "dimensions": dimensions},
            embedding_function=None,
        )
        expected = {"hnsw:space": "cosine", "embedding_model": model, "dimensions": dimensions}
        if any((self.collection.metadata or {}).get(k) != v for k, v in expected.items()):
            raise ValueError("Collection settings differ from the requested cosine model/dimensions")
        self.dimensions = dimensions

    def sync(self, records: list[dict]) -> tuple[int, int]:
        """Replace the complete collection snapshot; remove stale IDs after upserts."""
        if not records:
            raise ValueError("Refusing to synchronize an empty dataset")
        ids = [r["chunk_id"] for r in records]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate chunk IDs")
        metadatas = []
        for row in records:
            vector = row["embedding"]
            if (len(vector) != self.dimensions or
                    not all(isinstance(x, (int, float)) and math.isfinite(x) for x in vector) or
                    not any(vector)):
                raise ValueError(f"Invalid embedding for {row['chunk_id']}")
            if not isinstance(row.get("page"), int) or not row.get("source") or not row.get("document_id") or not row.get("text", "").strip():
                raise ValueError(f"Missing source, page, text or document ID: {row['chunk_id']}")
            metadata = dict(row.get("metadata", {}))
            if any(not isinstance(value, (str, int, float, bool)) for value in metadata.values()):
                raise ValueError(f"Unsupported metadata in {row['chunk_id']}")
            metadata.update(document_id=row["document_id"], source=row["source"], page=row["page"])
            metadatas.append(metadata)
        old_ids = set(self.collection.get(include=[])['ids'])
        for start in range(0, len(records), 500):
            batch = records[start:start + 500]
            self.collection.upsert(ids=ids[start:start + 500],
                                   embeddings=[r["embedding"] for r in batch],
                                   documents=[r["text"] for r in batch],
                                   metadatas=metadatas[start:start + 500])
        stale = sorted(old_ids - set(ids))
        for start in range(0, len(stale), 500):
            self.collection.delete(ids=stale[start:start + 500])
        return self.collection.count(), len(stale)

    def search(self, vector: list[float], top_k: int = 3, section: str | None = None):
        if top_k < 1 or len(vector) != self.dimensions or not all(math.isfinite(v) for v in vector) or not any(vector):
            raise ValueError("Invalid search vector or top_k")
        count = self.collection.count()
        if count == 0:
            return []
        kwargs = {"query_embeddings": [vector], "n_results": min(top_k, count),
                  "include": ["documents", "metadatas", "distances"]}
        if section:
            kwargs["where"] = {"section": section}
        result = self.collection.query(**kwargs)
        return [dict(chunk_id=key, text=text, metadata=metadata, cosine_distance=distance)
                for key, text, metadata, distance in zip(result["ids"][0], result["documents"][0],
                                                         result["metadatas"][0], result["distances"][0])]


def main():
    parser = argparse.ArgumentParser(description="Load or query the local Chroma collection")
    parser.add_argument("--db", default=DEFAULT_PATH)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="Synchronize the complete embedding snapshot")
    ingest.add_argument("input", type=Path)
    query = commands.add_parser("search", help="Embed a question and find similar chunks")
    query.add_argument("question")
    query.add_argument("--section")
    query.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if args.command == "ingest":
        report = json.loads(args.input.with_suffix(".report.json").read_text(encoding="utf-8"))
        if report["model"] != DEFAULT_MODEL or report["dimensions"] != 384 or report["chunks_exceeding_token_limit"] != 0:
            raise SystemExit("Embedding report must use the selected model with no over-limit chunks")
        with args.input.open(encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        if len(records) != report["chunks"]:
            raise SystemExit("Embedding report count does not match input")
        store = ChromaStore(args.db, args.collection, report["model"], report["dimensions"])
        count, deleted = store.sync(records)
        print(f"Collection: {args.collection}; stored: {count}; stale records removed: {deleted}; path: {args.db}")
    else:
        model = MyEmbedder(DEFAULT_MODEL)
        if len(model.model.tokenizer.encode(args.question, add_special_tokens=True, truncation=False)) > model.model.max_seq_length:
            raise SystemExit("Question exceeds the embedding model's token limit")
        store = ChromaStore(args.db, args.collection, model.model_name, model.dimensions)
        print(json.dumps(store.search(model.embed_query(args.question), args.top_k, args.section),
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
