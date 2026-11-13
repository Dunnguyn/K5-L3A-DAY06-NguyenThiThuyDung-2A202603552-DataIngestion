"""Local, non-destructive audit; counts are not human validity labels."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from pypdf import PdfReader
from .ingestion import normalize_text
from .evaluation import normalize

PDF = Path("starter/data/documents.pdf")
BENCHMARK = Path("starter/benchmark/sensor_questions.json")
MANIFEST = Path("data/manifest.json")


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["documents"][0]
    if not PDF.exists():
        raise SystemExit("NEEDS_VERIFICATION: original PDF missing")
    digest = hashlib.sha256(PDF.read_bytes()).hexdigest()
    if digest != manifest["sha256"]:
        raise SystemExit("NEEDS_VERIFICATION: PDF hash differs from manifest")
    pdf = PdfReader(PDF)
    selected = set(manifest["valid_pages"])
    texts, pages = {}, []
    for number, page in enumerate(pdf.pages, 1):
        try:
            text = normalize_text(page.extract_text() or "")
            error = None
        except Exception as exc:
            text, error = "", str(exc)
        texts[number] = text
        reason = ("extraction error: " + error if error else
                  "no extractable text" if not text else
                  "previously selected; content relevance and sufficiency need human review" if number in selected else
                  "previously excluded; exclusion needs human review")
        pages.append({"page": number, "normalized_characters": len(text),
                      "previously_selected": number in selected,
                      "validity": "NEEDS_VERIFICATION", "reason": reason})
    result = {"pdf_sha256": digest, "physical_pages": len(pages), "pages": pages,
              "selection_status": "NEEDS_VERIFICATION", "section_status": "NEEDS_VERIFICATION"}
    if BENCHMARK.exists():
        questions = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        checks = []
        for q in questions:
            page = q.get("gold_page")
            quote = q.get("evidence_quote", "")
            checks.append({"id": q.get("id"), "split": q.get("split"),
                "required_fields_present": all(q.get(k) for k in ("id", "split", "question", "expected_answer", "gold_source_id", "gold_page", "evidence_quote")),
                "gold_source_matches": q.get("gold_source_id") == manifest["source_id"],
                "quote_on_page_exact": bool(quote and normalize(quote) in normalize(texts.get(page, ""))),
                "filter_present": bool(q.get("filter")), "semantic_and_filter_review": "PENDING_MANUAL_REVIEW"})
        result["benchmark"] = {"count": len(questions), "split_counts": dict(Counter(q.get("split") for q in questions)),
            "unique_ids": len({q.get("id") for q in questions}) == len(questions), "questions": checks}
    else:
        result["benchmark"] = {"status": "NEEDS_VERIFICATION: benchmark missing"}
    out = Path("starter/results/sensor_verification.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PDF: {len(pages)} pages; previously selected: {len(selected)}; all validity decisions pending review")
    if "questions" in result["benchmark"]:
        b = result["benchmark"]
        print(f"Benchmark: {b['split_counts']}; exact quotes found: {sum(x['quote_on_page_exact'] for x in b['questions'])}/{b['count']}")
    print(f"Local report: {out}")

if __name__ == "__main__":
    main()
