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

# Headings verified in DOC001.  Matches can cross PDF line breaks.  Splitting
# at headings avoids assigning a whole page to the wrong section at a boundary.
DOC001_HEADINGS = (
    "Healthcare service system challenges",
    "Toward a Vision of People-Centered, Integrated, and Technology-Enabled Healthcare",
    "Leveraging Service Design for Healthcare Transformation",
    "Developing a research agenda for service design for healthcare transformation",
    "References",
    "Response to Reviewers",
)


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


def _clean_doc001_boilerplate(text: str) -> str:
    """Remove this PDF's identifiable journal headers and line-number footer."""
    text = re.sub(r"^Journal of Service Management\s*\n(?:\d+\s*\n)?", "", text)
    text = re.sub(
        r"(?:^|\n)Page \d+ of 52\s*\nhttp://mc\.manuscriptcentral\.com/josm"
        r"\s*\nJournal of Service Management(?:\s*\n\d+)*\s*$", "", text
    )
    return text


def _sections(text: str, current: str | None) -> tuple[list[tuple[str, str | None]], str | None]:
    matches = []
    for heading in DOC001_HEADINGS:
        pattern = r"(?im)^" + r"\s+".join(map(re.escape, heading.split())) + r"\s*$"
        matches.extend((m.start(), heading) for m in re.finditer(pattern, text))
    parts = []
    start = 0
    for pos, heading in sorted(matches):
        if text[start:pos].strip():
            parts.append((text[start:pos].strip(), current))
        current, start = heading, pos
    if text[start:].strip():
        parts.append((text[start:].strip(), current))
    return parts, current


def load_pdf(pdf_path: str | Path, document_id: str) -> list[DocumentPage]:
    """Extract pages; DOC001 pages crossing section headings become segments.

    `page` is always the original 1-based physical PDF page. An unrecognized
    section has no section metadata, rather than a guessed value.
    """
    path = Path(pdf_path)
    reader = PdfReader(path)
    pages: list[DocumentPage] = []
    section = None
    for number, page in enumerate(reader.pages, 1):
        try:
            text = normalize_text(page.extract_text() or "")
        except Exception:
            logger.exception("Cannot extract physical page %s from %s", number, path)
            continue
        if document_id == "DOC001":
            text = normalize_text(_clean_doc001_boilerplate(text))
            # The figure and table follow the reference list, without standard
            # section headings in the extracted text.
            if number == 40:
                section = "Figure"
            elif number == 41:
                section = "Table 1"
            if number < 6:
                parts = [(text, None)] if text else []
            else:
                parts, section = _sections(text, section)
        else:
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
    parser.add_argument("--document-id", default="DOC001")
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
