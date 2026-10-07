from __future__ import annotations

import json
import re

import jsonschema

from .base import CheckOutcome

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S | re.I)


def parse_json(text: str):
    t = text.strip()
    if m := _FENCE.match(t):
        t = m.group(1)
    return json.loads(t)


class JsonSchemaCheck:
    def __init__(self, schema: dict | None):
        self.schema = schema or {"type": "object"}
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def evaluate(self, prompt: str, answer: str, expected=None) -> CheckOutcome:
        try:
            doc = parse_json(answer)
        except (json.JSONDecodeError, ValueError) as exc:
            return CheckOutcome(False, f"not valid JSON: {exc}")
        errs = sorted(jsonschema.Draft202012Validator(self.schema).iter_errors(doc), key=lambda e: list(e.path))
        if errs:
            return CheckOutcome(False, f"schema violation: {errs[0].message[:120]}")
        return CheckOutcome(True, "valid JSON matching schema")
