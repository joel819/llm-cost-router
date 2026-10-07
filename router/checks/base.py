from __future__ import annotations

from dataclasses import dataclass, field

from ..cost import Usage


@dataclass
class CheckOutcome:
    passed: bool
    reason: str
    usage: Usage = field(default_factory=Usage)     # tokens spent by the check itself (judge only)
    judge_model: str | None = None
