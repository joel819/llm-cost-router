"""Run the 50-prompt benchmark: always-strongest baseline vs routed (cold cache) vs routed again (warm cache).

    python -m benchmark.run_benchmark [--limit N] [--out benchmark/out]

Everything in the report comes from these runs. Costs use config/prices.yaml; if a price is missing the cost
is reported as "not computed" — never estimated.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from router.config import Config, load_config
from router.cost import PriceBook, Usage
from router.errors import MissingPriceError, ProviderError
from router.providers import OpenAICompatProvider
from router.router import Router

from .report import build_report, render_markdown
from .scoring import is_correct

PROMPTS = Path(__file__).with_name("prompts.jsonl")


def load_prompts(path: Path = PROMPTS, limit: int | None = None) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return rows[:limit] if limit else rows


def _cost(prices: PriceBook, pairs):
    try:
        return sum(prices.cost(t.price_key, u) for t, u in pairs)
    except MissingPriceError:
        return None


def run_baseline(cfg: Config, provider, rows: list[dict]) -> list[dict]:
    """Every prompt goes straight to the strongest tier. No checks, no cache."""
    tier, prices, out = cfg.strongest, PriceBook(cfg.price_table), []
    for r in rows:
        task = cfg.task(r["task"])
        try:
            reply = provider.chat(tier, task.system, r["prompt"], task.max_tokens)
            text, usage, err = reply.text, reply.usage, None
        except ProviderError as exc:
            text, usage, err = "", Usage(), str(exc)[:200]
        out.append({"id": r["id"], "task": r["task"], "correct": is_correct(r["task"], text, r["expected"]) if not err else False,
                    "tier": tier.name, "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                    "cost": _cost(prices, [(tier, usage)]), "error": err, "answer": text[:200]})
    return out


def run_routed(router: Router, rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        try:
            res = router.complete(r["prompt"], r["task"])
            err = None
        except ProviderError as exc:
            out.append({"id": r["id"], "task": r["task"], "correct": False, "tier": None, "escalated": False, "cached": False,
                        "passed_check": False, "input_tokens": 0, "output_tokens": 0, "cost": None, "error": str(exc)[:200],
                        "answer": ""})
            continue
        out.append({"id": r["id"], "task": r["task"], "correct": is_correct(r["task"], res.text, r["expected"]),
                    "tier": res.tier, "escalated": len(res.attempts) > 1, "cached": res.cached, "passed_check": res.passed,
                    "input_tokens": res.input_tokens, "output_tokens": res.output_tokens, "cost": res.cost,
                    "error": err, "answer": res.text[:200]})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config-dir", default="config")
    ap.add_argument("--limit", type=int, help="only the first N prompts")
    ap.add_argument("--out", default="benchmark/out")
    a = ap.parse_args(argv)

    cfg = load_config(a.config_dir)
    provider = OpenAICompatProvider(cfg)
    rows = load_prompts(limit=a.limit)
    t0 = time.time()
    print(f"baseline: {len(rows)} prompts -> strongest tier ({cfg.strongest.provider}/{cfg.strongest.model})")
    baseline = run_baseline(cfg, provider, rows)
    router = Router(cfg, provider, ":memory:")
    print("routed (cold cache)")
    cold = run_routed(router, rows)
    print("routed again (warm cache)")
    warm = run_routed(router, rows)

    report = build_report(cfg, rows, baseline, cold, warm, elapsed=time.time() - t0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "report.md").write_text(render_markdown(report))
    print(render_markdown(report))
    print(f"\nwritten to {out}/report.md and report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
