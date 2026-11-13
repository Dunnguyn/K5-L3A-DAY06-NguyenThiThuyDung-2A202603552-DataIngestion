"""Evaluate retrieval using explicit evidence labels, never auto-score grounding."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def evidence_candidate(question: dict[str, Any], hit: dict[str, Any]) -> bool:
    """Recognize exact gold evidence on the right source/page; not a semantic judge."""
    meta = hit.get("metadata", {})
    return (meta.get("document_id") == question["gold_source_id"]
            and meta.get("page") == question["gold_page"]
            and normalize(question["evidence_quote"]) in normalize(hit.get("text", "")))


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]], labels: list[bool] | None = None) -> dict[str, Any]:
    """Require explicit reviewed labels; literal matching is only an aid."""
    if labels is None or len(labels) != len(hits) or any(type(x) is not bool for x in labels):
        raise ValueError("One reviewed boolean evidence label is required for each returned hit")
    return {"hit1": bool(labels and labels[0]), "hit3": any(labels[:3]),
            "labels": labels, "exact_candidates": [evidence_candidate(question, hit) for hit in hits]}


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    groups = defaultdict(list)
    for trace in traces:
        groups[(trace["strategy"], trace["split"])].append(trace)
    result = {}
    for (strategy, split), rows in sorted(groups.items()):
        count = len(rows)
        one, three = sum(r["hit1"] for r in rows), sum(r["hit3"] for r in rows)
        result[f"{strategy}_{split}"] = {"questions": count, "hit1_count": one, "hit1": one / count,
                                          "hit3_count": three, "hit3": three / count}
    return result


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
