"""Gold-answer scoring, independent of the router's own quality checks."""
from __future__ import annotations

import re

from router.checks.exact import normalise_answer
from router.checks.json_schema import parse_json


def _eq(a, b) -> bool:
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        try:
            return abs(float(a) - float(b)) < 1e-9
        except (TypeError, ValueError):
            return False
    return str(a).strip().casefold() == str(b).strip().casefold()


def is_correct(task: str, answer: str, expected) -> bool:
    if task == "classification":
        return normalise_answer(answer) == normalise_answer(expected)
    if task == "extraction":
        try:
            doc = parse_json(answer)
        except ValueError:
            return False
        return isinstance(doc, dict) and all(k in doc and _eq(doc[k], v) for k, v in expected.items())
    if task == "short_qa":
        text = answer.casefold()
        return any(re.search(rf"(?<!\w){re.escape(e.casefold())}(?!\w)", text) for e in expected)
    raise ValueError(f"no scorer for task {task!r}")
