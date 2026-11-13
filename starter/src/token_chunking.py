"""Split strategy B's chunks to fit the embedding model's token limit."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path

from .chunking import _chunk, by_paragraph
from .embeddings import DEFAULT_MODEL, MyEmbedder
from .models import DocumentPage


def token_bounded(page: DocumentPage, tokenizer, max_tokens: int, max_chars: int = 800):
    """Preserve all characters and prefer sentence/word boundaries when splitting.

    Offsets are relative to the original page segment, including when the
    preliminary paragraph chunk is subsequently split into smaller pieces.
    """
    if max_tokens <= tokenizer.num_special_tokens_to_add(pair=False):
        raise ValueError("Token limit must leave space for content")
    result = []
    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=True, truncation=False))

    for preliminary in by_paragraph(page, max_chars):
        start = preliminary.metadata['start_char']
        stop = preliminary.metadata['end_char']
        while start < stop:
            if count(page.text[start:stop]) <= max_tokens:
                end = stop
            else:
                # Search character positions and validate the selected slice;
                # tokenizer counts include the model's special tokens.
                low, high = start + 1, stop
                while low < high:
                    mid = (low + high + 1) // 2
                    if count(page.text[start:mid]) <= max_tokens:
                        low = mid
                    else:
                        high = mid - 1
                limit = low
                if count(page.text[start:limit]) > max_tokens:
                    raise ValueError("Token limit is too small for one character")
                portion = page.text[start:limit]
                sentences = list(re.finditer(r"[.!?][\"')\]]*\s+", portion))
                words = list(re.finditer(r"\s+", portion))
                # Avoid a tiny chunk when the only sentence boundary is near
                # the beginning; prefer a word boundary in that case.
                end = start + (sentences[-1].end() if sentences and sentences[-1].end() >= len(portion) // 2
                               else words[-1].end() if words else len(portion))
                while count(page.text[start:end]) > max_tokens:
                    end -= 1
                if end <= start:
                    raise ValueError("Unable to split text within token limit")
            result.append(_chunk(page, "paragraph_tokens", start, end))
            start = end
    return result


def main():
    parser = argparse.ArgumentParser(description="Create token-safe strategy B chunks")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise SystemExit("Input and output must differ")
    with args.input.open(encoding="utf-8") as f:
        pages = [DocumentPage(**json.loads(line)) for line in f if line.strip()]
    if not pages:
        raise SystemExit("Input has no document segments")
    embedder = MyEmbedder(args.model)
    tokenizer = embedder.model.tokenizer
    max_tokens = embedder.model.max_seq_length
    chunks = []
    for page in pages:
        parts = token_bounded(page, tokenizer, max_tokens)
        if ''.join(c.text for c in parts) != page.text:
            raise RuntimeError(f"Text lost on page {page.page}")
        chunks.extend(parts)
    if len({c.chunk_id for c in chunks}) != len(chunks):
        raise RuntimeError("Duplicate chunk IDs")
    lengths = [len(tokenizer.encode(c.text, add_special_tokens=True, truncation=False)) for c in chunks]
    if any(n > max_tokens for n in lengths):
        raise RuntimeError("A chunk exceeds the token limit")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + '\n')
    print(f"Created {len(chunks)} chunks; token lengths {min(lengths)}–{max(lengths)}; limit {max_tokens}; {args.output}")


if __name__ == "__main__":
    main()
