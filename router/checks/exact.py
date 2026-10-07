from __future__ import annotations

import re

from .base import CheckOutcome


def normalise_answer(s: str) -> str:
    s = s.strip().strip("\"'`").strip()
    s = re.sub(r"[.!\s]+$", "", s)
    return s.lower()


class ExactCheck:
    """The answer must equal an allowed output — or the request's own `expected` value when one is given."""

    def __init__(self, allowed: tuple[str, ...]):
        self.allowed = tuple(normalise_answer(a) for a in allowed)

    def evaluate(self, prompt: str, answer: str, expected: str | None = None) -> CheckOutcome:
        got = normalise_answer(answer)
        if expected is not None:
            ok = got == normalise_answer(expected)
            return CheckOutcome(ok, "matches expected" if ok else f"expected {expected!r}, got {answer[:60]!r}")
        if not self.allowed:
            return CheckOutcome(False, "no allowed outputs configured for this task")
        ok = got in self.allowed
        return CheckOutcome(ok, "in allowed set" if ok else f"{answer[:60]!r} is not one of the allowed outputs")
