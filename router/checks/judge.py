"""LLM-as-judge, always run by the strongest tier."""
from __future__ import annotations

import json
import re

from ..config import Tier
from .base import CheckOutcome

JUDGE_SYSTEM = ("You are a strict grader. Given a task, a rubric and a candidate answer, decide whether the answer "
                'passes. Reply with JSON only: {"pass": true|false, "reason": "<short>"}.')


def parse_verdict(text: str) -> tuple[bool, str] | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(d.get("pass"), bool):
        return None
    return d["pass"], str(d.get("reason", ""))[:200]


class JudgeCheck:
    def __init__(self, provider, judge_tier: Tier, rubric: str):
        self.provider, self.tier, self.rubric = provider, judge_tier, rubric

    def evaluate(self, prompt: str, answer: str, expected=None) -> CheckOutcome:
        user = f"TASK / QUESTION:\n{prompt}\n\nRUBRIC:\n{self.rubric}\n\nCANDIDATE ANSWER:\n{answer}"
        reply = self.provider.chat(self.tier, JUDGE_SYSTEM, user, 400)
        verdict = parse_verdict(reply.text)
        if verdict is None:     # fail closed: an unreadable verdict never counts as a pass
            return CheckOutcome(False, "judge returned an unreadable verdict", reply.usage, self.tier.model)
        return CheckOutcome(verdict[0], verdict[1] or ("judge: pass" if verdict[0] else "judge: fail"),
                            reply.usage, self.tier.model)
