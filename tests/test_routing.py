import pytest

from router.errors import ProviderError


def test_cheap_tier_answer_that_passes_is_used_without_escalation(build):
    r, prov = build({"cheap": ["positive"], "strong": ["positive"]})
    res = r.complete("great product", "classification")
    assert (res.tier, res.passed, res.cached) == ("cheap", True, False)
    assert prov.count("cheap") == 1 and prov.count("strong") == 0


def test_failed_check_escalates_to_next_tier(build):
    r, prov = build({"cheap": ["I think it's kind of positive, maybe"], "strong": ["negative"]})
    res = r.complete("awful", "classification")
    assert res.tier == "strong" and res.text == "negative" and res.passed
    assert [(a.tier, a.passed) for a in res.attempts] == [("cheap", False), ("strong", True)]
    assert prov.count("cheap") == 1 and prov.count("strong") == 1


def test_json_schema_failure_escalates(build):
    r, _ = build({"cheap": ['Sure! {"name": "Ada"}'], "strong": ['{"name": "Ada"}']})
    res = r.complete("extract the name from: Ada", "extraction")
    assert res.tier == "strong" and res.passed


def test_json_in_code_fence_is_accepted_on_first_tier(build):
    r, prov = build({"cheap": ['```json\n{"name": "Ada"}\n```'], "strong": ["unused"]})
    assert r.complete("p", "extraction").tier == "cheap" and prov.count("strong") == 0


def test_schema_violation_escalates(build):
    r, _ = build({"cheap": ['{"name": 5}'], "strong": ['{"name": "Ada"}']})
    assert r.complete("p", "extraction").tier == "strong"


def test_expected_overrides_allowed_set(build):
    r, _ = build({"cheap": ["positive"], "strong": ["negative"]})
    res = r.complete("p", "classification", expected="negative")
    assert res.tier == "strong"


def test_judge_pass_keeps_cheap_answer_and_judge_runs_on_strongest(build):
    r, prov = build({"cheap": ["Canberra"], "strong": ['{"pass": true, "reason": "correct"}']})
    res = r.complete("Capital of Australia?", "short_qa")
    assert res.tier == "cheap" and res.passed
    assert prov.count("strong") == 1                 # the judge call
    assert res.attempts[0].judge_input_tokens == 100


def test_judge_fail_escalates_and_strongest_is_not_self_judged(build):
    r, prov = build({"cheap": ["Sydney"], "strong": ['{"pass": false, "reason": "wrong"}', "Canberra"]})
    res = r.complete("Capital of Australia?", "short_qa")
    assert res.tier == "strong" and res.text == "Canberra" and res.passed
    assert prov.count("strong") == 2                 # 1 judge + 1 answer, no second judge


def test_unreadable_judge_verdict_fails_closed(build):
    r, _ = build({"cheap": ["Canberra"], "strong": ["looks fine to me", "Canberra"]})
    assert r.complete("q", "short_qa").tier == "strong"


def test_all_tiers_failing_returns_last_answer_unpassed_and_uncached(build):
    r, prov = build({"cheap": ["meh"], "strong": ["still meh"]})
    res = r.complete("p", "classification")
    assert (res.passed, res.tier, res.text) == (False, "strong", "still meh")
    r.complete("p", "classification")
    assert prov.count("cheap") == 2                   # failures are not cached


def test_provider_error_on_cheap_tier_escalates(build):
    r, _ = build({"cheap": [ProviderError("rate limited")], "strong": ["positive"]})
    res = r.complete("p", "classification")
    assert res.tier == "strong" and res.attempts[0].error


def test_when_escalation_target_is_down_the_best_answer_so_far_is_returned_unpassed(build):
    r, _ = build({"cheap": ["nope"], "strong": [ProviderError("down")]})
    res = r.complete("p", "classification")
    assert (res.text, res.passed, res.tier) == ("nope", False, "cheap")
    assert res.attempts[-1].error


def test_all_providers_down_raises(build):
    r, _ = build({"cheap": [ProviderError("a")], "strong": [ProviderError("b")]})
    with pytest.raises(ProviderError):
        r.complete("p", "classification")


def test_unknown_task_type(build):
    from router.errors import ConfigError
    r, _ = build({})
    with pytest.raises(ConfigError, match="unknown task type"):
        r.complete("p", "poetry")
