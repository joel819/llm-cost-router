from router.cache import cache_key, normalise


def test_repeat_is_a_cache_hit_and_makes_no_api_call(build):
    r, prov = build({"cheap": ["positive"], "strong": ["positive"]})
    first = r.complete("great", "classification")
    second = r.complete("great", "classification")
    assert not first.cached and second.cached
    assert second.text == first.text and second.tier == first.tier
    assert len(prov.calls) == 1                       # the second request never reached a provider
    assert second.cost == 0.0 and second.input_tokens == 0 and second.output_tokens == 0


def test_whitespace_variants_share_a_key():
    assert cache_key("a   b\n c", "t") == cache_key(" a b c ", "t")
    assert normalise("ｆｕｌｌ  width") == "full width"        # NFKC


def test_case_and_task_type_change_the_key():
    assert cache_key("Hello", "t") != cache_key("hello", "t")
    assert cache_key("Hello", "a") != cache_key("Hello", "b")


def test_escalated_answer_is_cached_with_its_tier(build):
    r, prov = build({"cheap": ["??"], "strong": ["negative"]})
    r.complete("bad", "classification")
    hit = r.complete("bad", "classification")
    assert hit.cached and hit.tier == "strong" and len(prov.calls) == 2


def test_cache_can_be_disabled(build):
    r, prov = build({"cheap": ["positive"]}, use_cache=False)
    r.complete("x", "classification")
    r.complete("x", "classification")
    assert len(prov.calls) == 2


def test_expected_value_is_part_of_the_key(build):
    r, prov = build({"cheap": ["positive"], "strong": ["negative"]})
    r.complete("x", "classification")
    res = r.complete("x", "classification", expected="negative")
    assert not res.cached


def test_cache_persists_in_sqlite_file(tmp_path, cfg):
    from router.router import Router
    from tests.conftest import FakeProvider
    db = str(tmp_path / "r.db")
    Router(cfg, FakeProvider({"cheap": ["positive"]}), db).complete("x", "classification")
    prov = FakeProvider({})
    again = Router(cfg, prov, db).complete("x", "classification")
    assert again.cached and prov.calls == []
