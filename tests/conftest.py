import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router.config import Config, Provider, Task, Tier  # noqa: E402
from router.cost import Usage  # noqa: E402
from router.errors import ProviderError  # noqa: E402
from router.providers import Reply  # noqa: E402
from router.router import Router  # noqa: E402


class FakeProvider:
    """Mocked providers: per-model scripted answers; records every call. Never touches the network."""

    def __init__(self, answers: dict[str, list]):
        self.answers = {k: list(v) for k, v in answers.items()}
        self.calls: list[tuple[str, str]] = []          # (model, user prompt)

    def chat(self, tier, system, user, max_tokens):
        self.calls.append((tier.model, user))
        queue = self.answers.get(tier.model)
        if not queue:
            raise AssertionError(f"unexpected call to {tier.model}")
        a = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(a, Exception):
            raise a
        return Reply(a, Usage(100, 10))

    def count(self, model):
        return sum(1 for m, _ in self.calls if m == model)


PRICES = {
    "p/cheap": {"input_per_million": 1.0, "output_per_million": 2.0},
    "p/strong": {"input_per_million": 10.0, "output_per_million": 20.0},
}


def make_cfg(prices=PRICES) -> Config:
    tasks = {
        "classification": Task("classification", "classify", "exact", 50, allowed=("positive", "negative")),
        "extraction": Task("extraction", "extract", "json_schema", 100,
                           schema={"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}),
        "short_qa": Task("short_qa", "answer", "judge", 100, rubric="must be correct"),
    }
    return Config({"p": Provider("p", "http://x", "K")}, [Tier("cheap", "p", "cheap"), Tier("strong", "p", "strong")],
                  tasks, prices)


@pytest.fixture
def cfg():
    return make_cfg()


@pytest.fixture
def build(cfg):
    def _build(answers, **kw):
        prov = FakeProvider(answers)
        return Router(cfg, prov, ":memory:", **kw), prov
    return _build
