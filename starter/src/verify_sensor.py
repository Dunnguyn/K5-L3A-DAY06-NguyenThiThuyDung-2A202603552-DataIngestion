"""Validate the archived traces, PDF offsets and score tables without embedding."""
import csv
import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from .evaluation import evaluate_query, evidence_candidate, load_jsonl, normalize, summarize
from .sensor_prepare import prepare

ARCHIVE = Path("starter/results/sensor_run/evaluation")


def read_json(path):
    return Path(path).read_text(encoding="utf-8")


def table(name):
    with Path("review", name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    with TemporaryDirectory() as tmp:
        output = Path(tmp) / "pages.jsonl"
        prepare(output)
        pages = {p["page"]: p for p in load_jsonl(output)}
    questions = json.loads(read_json("starter/benchmark/sensor_questions.json"))
    assert len({q["id"] for q in questions}) == len(questions)
    counts = Counter(q["split"] for q in questions)
    assert counts["dev"] >= 15 and counts["test"] >= 5
    filtered = [q for q in questions if q.get("filter")]
    assert len(filtered) >= 3 and any(q["split"] == "test" for q in filtered)
    for q in questions:
        page = pages[q["gold_page"]]
        assert q["question"].strip() and q["expected_answer"].strip() and q["evidence_quote"].strip()
        assert q["gold_source_id"] == page["document_id"]
        assert normalize(q["evidence_quote"]) in normalize(page["text"])
        if q.get("filter"):
            assert q["filter"] == {"section": page["metadata"]["section"]}
    questions = {q["id"]: q for q in questions}
    reviewed = {(r["id"], r["cau_hinh"], int(r["rank"])): r for r in table("retrieval_review.csv")}
    semantic = []
    for split in ("dev", "test"):
        traces = load_jsonl(ARCHIVE / f"{split}_exact_review.jsonl")
        expected = {(q["id"], s) for q in questions.values() if q["split"] == split for s in "ABC"}
        assert len(traces) == len(expected) and {(t["question_id"], t["strategy"]) for t in traces} == expected
        exact = []
        for trace in traces:
            q = questions[trace["question_id"]]
            strategy = trace["strategy"]
            hits = trace["results"]
            assert trace["split"] == q["split"] and trace["question"] == q["question"]
            assert len(hits) == 3 and trace["filter_applied"] == (q.get("filter") if strategy == "C" else None)
            labels = []
            for rank, hit in enumerate(hits, 1):
                meta = hit["metadata"]
                page = pages[meta["page"]]
                assert hit.get("rank", rank) == rank and isinstance(hit["cosine_distance"], (float, int))
                assert all(meta[k] == page[k] for k in ("document_id", "source"))
                assert meta["section"] == page["metadata"]["section"]
                assert hit["text"] == page["text"][meta["start_char"]:meta["end_char"]]
                if trace["filter_applied"]:
                    assert meta["section"] == q["filter"]["section"]
                row = reviewed.pop((q["id"], strategy, rank))
                assert hit["chunk_id"] == row["chunk_id"]
                labels.append(row["nhan_evidence_du"] == "Có")
            exact.append({**trace, **evaluate_query(q, hits, [evidence_candidate(q, h) for h in hits])})
            semantic.append({**trace, **evaluate_query(q, hits, labels)})
        assert summarize(exact) == json.loads(read_json(ARCHIVE / f"{split}_exact_metrics.json"))
    assert not reviewed
    assert summarize(semantic) == json.loads(read_json("artifacts/sensor_semantic_metrics.json"))["metrics"]
    scores = table("manual_scoring_review.csv")
    summary = json.loads(read_json("artifacts/sensor_review_summary_semantic.json"))
    for strategy, stats in summary.items():
        group = [r for r in scores if r["cau_hinh"] == strategy]
        for kind, n in (("coherence", 10), ("grounding", 5)):
            rows = [r for r in group if r["nhom"] == kind]
            assert len(rows) == n and all(r["ly_do"] for r in rows)
            values = [int(r["diem_0_1_2"]) for r in rows]
            assert sum(values) / n == stats[kind + "_mean"]
            if kind == "grounding":
                assert [values.count(i) for i in range(3)] == stats["grounding_0_1_2"]
            else:
                assert {int(r["trang_pdf"]) for r in rows} == set(sorted(pages)[:10])
        assert sum(r["nhom"] == "metadata" and r["metadata_du_va_dung"] == "Khớp kiểm tra tự động" for r in group) == stats["metadata_correct"] == 15
    print("Verified corpus, benchmark, 180 ranked hits, exact/semantic metrics and review tables.")


if __name__ == "__main__":
    main()
