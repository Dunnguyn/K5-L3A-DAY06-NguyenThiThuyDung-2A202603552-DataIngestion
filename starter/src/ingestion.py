"""Read PDF text, retain physical page numbers, and normalize whitespace."""

from __future__ import annotations

import argparse
import json
import logging
import re
import unicodedata
from dataclasses import asdict
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize Unicode and spacing while keeping line/paragraph boundaries."""
    text = unicodedata.normalize("NFC", text).replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t \u00a0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def clean_text(text: str) -> str:
    """Backward-compatible name used by the earlier exercise."""
    return normalize_text(text)


def load_pdf(pdf_path: str | Path, document_id: str) -> list[DocumentPage]:
    """Extract text by physical page; do not infer section metadata."""
    path = Path(pdf_path)
    reader = PdfReader(path)
    pages: list[DocumentPage] = []
    for number, page in enumerate(reader.pages, 1):
        try:
            text = normalize_text(page.extract_text() or "")
        except Exception:
            logger.exception("Cannot extract physical page %s from %s", number, path)
            continue
        parts = [(text, None)] if text else []
        if not parts:
            logger.warning("No extractable text on physical page %s of %s", number, path)
        for content, section_name in parts:
            metadata = {"section": section_name} if section_name else {}
            pages.append(DocumentPage(document_id, str(path), number, content, metadata))
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a PDF into JSON Lines")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--document-id", default="DOCUMENT")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.output.with_suffix(".log")
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_path, encoding="utf-8")],
    )
    pages = load_pdf(args.pdf, args.document_id)
    if not pages:
        raise SystemExit("No text was extracted; check the PDF or whether OCR is needed.")
    with args.output.open("w", encoding="utf-8") as output:
        for page in pages:
            output.write(json.dumps(asdict(page), ensure_ascii=False) + "\n")
    print(f"Extracted {len(pages)} segments from {len({p.page for p in pages})} pages into {args.output}")
    print(f"Warnings and errors: {log_path}")
    print("This is not a count of valid content pages; review the corpus separately.")


if __name__ == "__main__":
    main()
