from __future__ import annotations

import argparse
import json
import os
import sys

from . import usage as usage_log
from .config import load_config
from .errors import RouterError
from .providers import OpenAICompatProvider
from .router import Router


def _router(a) -> Router:
    cfg = load_config(a.config_dir)
    return Router(cfg, OpenAICompatProvider(cfg), a.db, strict_costs=getattr(a, "strict_costs", False))


def cmd_complete(a) -> int:
    res = _router(a).complete(a.prompt, a.task, a.expected)
    if a.json:
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(res.text)
        path = " → ".join(f"{x.tier}{'✓' if x.passed else '✗'}" for x in res.attempts) or "(cache)"
        cost = "cache hit, $0" if res.cached else (f"${res.cost:.6f}" if res.cost is not None else "cost not computed (fill in config/prices.yaml)")
        print(f"\n[{res.tier} · {path} · {res.input_tokens}+{res.output_tokens} tokens · {cost}]", file=sys.stderr)
    return 0 if res.passed else 3


def cmd_check_models(a) -> int:
    cfg = load_config(a.config_dir)
    provider = OpenAICompatProvider(cfg)
    bad = 0
    for pname in sorted({t.provider for t in cfg.tiers}):
        p = cfg.providers[pname]
        try:
            ids = set(provider.list_models(pname))
        except RouterError as exc:
            print(f"{pname}: could not list models — {exc}")
            bad += 1
            continue
        print(f"{pname} ({p.base_url}): {len(ids)} models listed")
        for t in cfg.tiers:
            if t.provider == pname:
                ok = t.model in ids
                bad += not ok
                print(f"  {'OK     ' if ok else 'MISSING'} tier {t.name:<8} {t.model}")
    return 1 if bad else 0


def cmd_bench(a) -> int:
    from benchmark.run_benchmark import main as bench_main
    return bench_main(["--config-dir", a.config_dir] + (["--limit", str(a.limit)] if a.limit else []) + ["--out", a.out])


def cmd_stats(a) -> int:
    print(json.dumps(usage_log.summary(_router(a).conn), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m router", description="Route prompts to the cheapest model that passes a quality check.")
    ap.add_argument("--config-dir", default=os.getenv("ROUTER_CONFIG_DIR", "config"))
    ap.add_argument("--db", default=os.getenv("ROUTER_DB", "data/router.db"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("complete", help="route one prompt")
    c.add_argument("prompt")
    c.add_argument("--task", required=True, help="task type from config/tasks.yaml")
    c.add_argument("--expected", help="exact-match target for this prompt (overrides the task's allowed set)")
    c.add_argument("--json", action="store_true")
    c.add_argument("--strict-costs", action="store_true", help="error out instead of reporting 'cost not computed'")
    c.set_defaults(fn=cmd_complete)
    sub.add_parser("check-models", help="verify every tier's model id exists at its provider").set_defaults(fn=cmd_check_models)
    b = sub.add_parser("bench", help="run the 50-prompt benchmark")
    b.add_argument("--limit", type=int)
    b.add_argument("--out", default="benchmark/out")
    b.set_defaults(fn=cmd_bench)
    sub.add_parser("stats", help="usage summary from the log").set_defaults(fn=cmd_stats)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except RouterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
