"""Extract the manifest snapshot and retain physical page provenance."""
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader
from .ingestion import normalize_text


def prepare(output: Path):
    document = json.loads(Path("data/manifest.json").read_text(encoding="utf-8"))["documents"][0]
    source = Path(document["source_path_or_url"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != document["sha256"]:
        raise ValueError("PDF checksum differs from the manifest")
    pdf = PdfReader(source)
    if len(pdf.pages) != document["physical_pages"]:
        raise ValueError("Unexpected physical page count")
    if [p["page"] for p in document["pages"]] != document["valid_pages"]:
        raise ValueError("Page metadata differs from selected pages")
    rows = []
    for entry in document["pages"]:
        number = entry["page"]
        try:
            text = normalize_text(pdf.pages[number - 1].extract_text() or "")
        except Exception as exc:
            raise ValueError(f"Failed to extract page {number}") from exc
        if not text or len(text) != entry["characters"]:
            raise ValueError(f"Unexpected extracted text length on page {number}")
        rows.append({"document_id": document["source_id"], "source": source.as_posix(),
                     "page": number, "text": text, "metadata": {"section": entry["section"]}})
    with output.open("x", encoding="utf-8") as stream:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False), file=stream)
    print(f"{len(rows)} pages -> {output}")
