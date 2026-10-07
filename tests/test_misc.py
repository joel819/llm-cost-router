import pytest
from fastapi.testclient import TestClient

from benchmark.scoring import is_correct
from router import usage
from router.api import create_app
from router.config import load_config
from router.errors import ConfigError


def test_shipped_config_loads():
    cfg = load_config("config")
    assert [t.name for t in cfg.tiers][0] == "small" and cfg.strongest.name == "strong"
    assert {"classification", "extraction", "short_qa"} <= set(cfg.tasks)


def test_bad_config_is_reported(tmp_path):
    (tmp_path / "tiers.yaml").write_text("providers: {}\ntiers: []\n")
    (tmp_path / "prices.yaml").write_text("models: {}\n")
    (tmp_path / "tasks.yaml").write_text("tasks: {}\n")
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_api_complete_and_usage(build):
    r, _ = build({"cheap": ["positive"]})
    c = TestClient(create_app(r))
    with c:
        a = c.post("/complete", json={"prompt": "great", "task_type": "classification"}).json()
        b = c.post("/complete", json={"prompt": "great", "task_type": "classification"}).json()
        assert a["tier"] == "cheap" and not a["cached"] and b["cached"]
        u = c.get("/usage").json()
        assert u["requests"] == 2 and u["cache_hits"] == 1
        assert c.post("/complete", json={"prompt": "x", "task_type": "nope"}).status_code == 422
        assert c.post("/complete", json={"prompt": "", "task_type": "classification"}).status_code == 422


def test_api_provider_failure_is_502(build):
    from router.errors import ProviderError
    r, _ = build({"cheap": [ProviderError("a")], "strong": [ProviderError("b")]})
    with TestClient(create_app(r)) as c:
        assert c.post("/complete", json={"prompt": "x", "task_type": "classification"}).status_code == 502


def test_usage_summary_flags_unpriced_requests(build):
    from tests.conftest import make_cfg, FakeProvider
    from router.router import Router
    r = Router(make_cfg(prices={}), FakeProvider({"cheap": ["positive"]}), ":memory:")
    r.complete("x", "classification")
    s = usage.summary(r.conn)
    assert s["cost_usd"] is None and s["requests_without_price"] == 1


@pytest.mark.parametrize("task,answer,expected,ok", [
    ("classification", " Positive. ", "positive", True), ("classification", "negative", "positive", False),
    ("extraction", '{"a": "X", "n": 5.0, "extra": 1}', {"a": "x", "n": 5}, True),
    ("extraction", '{"a": "y"}', {"a": "x"}, False), ("extraction", "not json", {"a": "x"}, False),
    ("short_qa", "It is Au.", ["au"], True), ("short_qa", "Australia", ["au"], False),
    ("short_qa", "100 °C", ["100"], True), ("short_qa", "1100", ["100"], False),
])
def test_gold_scoring(task, answer, expected, ok):
    assert is_correct(task, answer, expected) is ok


def test_benchmark_dataset_shape():
    import json
    rows = [json.loads(l) for l in open("benchmark/prompts.jsonl")]
    assert len(rows) == 50 and len({r["id"] for r in rows}) == 50
    assert {r["task"] for r in rows} == {"classification", "extraction", "short_qa"}
