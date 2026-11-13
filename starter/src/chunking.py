"""Two deterministic chunking strategies with source and page traceability."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from dataclasses import asdict
from pathlib import Path

from .models import Chunk, DocumentPage


def _chunk(page: DocumentPage, strategy: str, start: int, end: int) -> Chunk:
    # Include segment text and metadata because one physical page may contain
    # multiple sections, each starting at offset zero.
    identity = json.dumps([page.document_id, page.page, page.text, page.metadata],
                          ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return Chunk(
        chunk_id=f"{page.document_id}_p{page.page}_{strategy}_{digest}_{start}_{end}",
        document_id=page.document_id, source=page.source, page=page.page,
        text=page.text[start:end], metadata={**page.metadata, "start_char": start, "end_char": end},
    )


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Cut fixed-size character windows; offsets refer to the input segment."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("size must be positive and 0 <= overlap < size")
    chunks = []
    for start in range(0, len(page.text), size - overlap):
        end = min(start + size, len(page.text))
        chunks.append(_chunk(page, "fixed", start, end))
        if end == len(page.text):
            break
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Prefer paragraph, sentence, then whitespace boundaries within max_size.

    PDF extraction does not always mark paragraphs. If no blank lines remain,
    sentence/word boundaries are a fallback, not verified paragraph structure.
    """
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    text = page.text
    paragraph_ends = [m.end() for m in re.finditer(r"\n\s*\n", text)]
    sentence_ends = [m.end() for m in re.finditer(r"[.!?][\"')\]]*\s+", text)]
    whitespace_ends = [m.end() for m in re.finditer(r"\s+", text)]
    chunks = []
    start = 0
    while start < len(text):
        limit = min(start + max_size, len(text))
        if limit == len(text):
            end = limit
        else:
            end = 0
            for boundaries in (paragraph_ends, sentence_ends, whitespace_ends):
                candidates = [pos for pos in boundaries if start < pos <= limit]
                if candidates:
                    end = candidates[-1]
                    break
            if not end:
                end = limit  # A single unbroken word longer than max_size.
        chunks.append(_chunk(page, "paragraph", start, end))
        start = end
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Create fixed and paragraph chunks from JSONL")
    parser.add_argument("input", type=Path, help="JSONL produced by ingestion")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as source:
        pages = [DocumentPage(**json.loads(line)) for line in source if line.strip()]
    if not pages:
        raise SystemExit("Input has no document segments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, build in (("fixed", lambda p: fixed_size(p, 500, 50)),
                        ("paragraph", lambda p: by_paragraph(p, 800))):
        chunks = [chunk for page in pages for chunk in build(page)]
        ids = [chunk.chunk_id for chunk in chunks]
        if len(ids) != len(set(ids)):
            raise SystemExit(f"Duplicate {name} chunk IDs; inspect duplicate input segments.")
        path = args.output_dir / f"chunks_{name}.jsonl"
        with path.open("w", encoding="utf-8") as output:
            for chunk in chunks:
                output.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
        lengths = [len(chunk.text) for chunk in chunks]
        print(f"{name}: {len(chunks)} chunks; lengths min/mean/max = "
              f"{min(lengths)}/{statistics.mean(lengths):.1f}/{max(lengths)}; {path}")


if __name__ == "__main__":
    main()
