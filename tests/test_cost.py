import pytest

from router.cost import PriceBook, Usage
from router.errors import MissingPriceError
from tests.conftest import PRICES, make_cfg


def test_cost_arithmetic():
    pb = PriceBook(PRICES)
    assert pb.cost("p/cheap", Usage(1_000_000, 500_000)) == pytest.approx(1.0 * 1 + 2.0 * 0.5)


def test_free_models_are_an_explicit_zero():
    pb = PriceBook({"p/free": {"input_per_million": 0.0, "output_per_million": 0.0}})
    assert pb.cost("p/free", Usage(10, 10)) == 0.0


@pytest.mark.parametrize("table", [{}, {"p/cheap": {"input_per_million": None, "output_per_million": None}},
                                   {"p/cheap": {"input_per_million": 1.0, "output_per_million": None}}])
def test_missing_price_raises_a_clear_error_instead_of_guessing(table):
    with pytest.raises(MissingPriceError, match="prices.yaml"):
        PriceBook(table).cost("p/cheap", Usage(10, 10))


def test_negative_or_non_numeric_price_rejected():
    with pytest.raises(MissingPriceError):
        PriceBook({"p/cheap": {"input_per_million": -1, "output_per_million": 1}}).cost("p/cheap", Usage(1, 1))
    with pytest.raises(MissingPriceError):
        PriceBook({"p/cheap": {"input_per_million": "cheap", "output_per_million": 1}}).cost("p/cheap", Usage(1, 1))


def test_request_cost_includes_failed_attempt_and_judge(build):
    r, _ = build({"cheap": ["Sydney"], "strong": ['{"pass": false, "reason": "x"}', "Canberra"]})
    res = r.complete("q", "short_qa")
    # cheap answer (100/10) + judge on strong (100/10) + strong answer (100/10)
    expected = (100 * 1 + 10 * 2) / 1e6 + 2 * (100 * 10 + 10 * 20) / 1e6
    assert res.cost == pytest.approx(expected)
    assert (res.input_tokens, res.output_tokens) == (300, 30)


def test_missing_price_is_reported_not_invented_in_normal_mode(cfg):
    from router.router import Router
    from tests.conftest import FakeProvider
    cfg2 = make_cfg(prices={})
    res = Router(cfg2, FakeProvider({"cheap": ["positive"]}), ":memory:").complete("x", "classification")
    assert res.cost is None and "prices.yaml" in res.cost_note
    assert res.input_tokens == 100                    # tokens are still measured


def test_strict_mode_raises_on_missing_price():
    from router.router import Router
    from tests.conftest import FakeProvider
    r = Router(make_cfg(prices={}), FakeProvider({"cheap": ["positive"]}), ":memory:", strict_costs=True)
    with pytest.raises(MissingPriceError):
        r.complete("x", "classification")


def test_shipped_prices_file_has_only_placeholders():
    import yaml
    d = yaml.safe_load(open("config/prices.yaml"))["models"]
    assert d and all(v["input_per_million"] is None and v["output_per_million"] is None for v in d.values())
