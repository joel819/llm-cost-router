from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone


def _sum(rows, k):
    return sum(r[k] for r in rows)


def _total_cost(rows):
    costs = [r["cost"] for r in rows]
    return None if any(c is None for c in costs) else sum(costs)


def _mode(rows):
    n = len(rows)
    return {"prompts": n, "correct": sum(r["correct"] for r in rows), "pass_rate": sum(r["correct"] for r in rows) / n if n else 0,
            "input_tokens": _sum(rows, "input_tokens"), "output_tokens": _sum(rows, "output_tokens"),
            "cost_usd": _total_cost(rows), "errors": sum(1 for r in rows if r.get("error"))}


def build_report(cfg, prompts, baseline, cold, warm, elapsed: float) -> dict:
    base, rc, rw = _mode(baseline), _mode(cold), _mode(warm)
    tiers = Counter(r["tier"] for r in cold)
    by_task = {}
    for t in sorted({r["task"] for r in cold}):
        b = [r for r in baseline if r["task"] == t]
        c = [r for r in cold if r["task"] == t]
        by_task[t] = {"prompts": len(c), "baseline_correct": sum(r["correct"] for r in b), "routed_correct": sum(r["correct"] for r in c),
                      "final_tier": dict(Counter(r["tier"] for r in c))}
    savings = None
    if base["cost_usd"] is not None and rc["cost_usd"] is not None and base["cost_usd"] > 0:
        savings = {"baseline_usd": base["cost_usd"], "routed_usd": rc["cost_usd"],
                   "saved_pct": 100 * (1 - rc["cost_usd"] / base["cost_usd"])}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tiers": [{"name": t.name, "provider": t.provider, "model": t.model} for t in cfg.tiers],
        "strongest": cfg.strongest.model, "elapsed_seconds": round(elapsed, 1),
        "baseline_always_strongest": base, "routed_cold": rc, "routed_warm": rw,
        "final_tier_counts": dict(tiers),
        "escalated": sum(1 for r in cold if r["escalated"]),
        "cache_hits_warm_pass": sum(1 for r in warm if r["cached"]),
        "by_task": by_task, "savings": savings,
        "prices_filled": all(r["cost"] is not None for r in baseline + cold if not r.get("error")) if baseline else False,
        "per_prompt": [{"id": c["id"], "task": c["task"], "baseline_correct": b["correct"], "routed_correct": c["correct"],
                        "final_tier": c["tier"], "escalated": c["escalated"], "warm_cache_hit": w["cached"],
                        "routed_tokens": c["input_tokens"] + c["output_tokens"],
                        "baseline_tokens": b["input_tokens"] + b["output_tokens"]}
                       for b, c, w in zip(baseline, cold, warm)],
    }


def _usd(v):
    return "not computed — fill in config/prices.yaml" if v is None else f"${v:.6f}"


def render_markdown(r: dict) -> str:
    b, c, w = r["baseline_always_strongest"], r["routed_cold"], r["routed_warm"]
    L = [f"# Benchmark report — {r['generated_at']}", "",
         "Tiers (cheapest first): " + " → ".join(f"`{t['provider']}/{t['model']}`" for t in r["tiers"]),
         f"Baseline = every prompt sent to the strongest tier (`{r['strongest']}`).", "",
         "| | prompts | correct (gold) | pass rate | input tokens | output tokens | cost |", "|---|---|---|---|---|---|---|"]
    for name, m in (("always strongest", b), ("routed (cold cache)", c), ("routed again (warm cache)", w)):
        L.append(f"| {name} | {m['prompts']} | {m['correct']} | {m['pass_rate']:.0%} | {m['input_tokens']} | {m['output_tokens']} | {_usd(m['cost_usd'])} |")
    L += ["", f"Routed final tier: {r['final_tier_counts']} · escalations: {r['escalated']} · "
              f"cache hits on the second pass: {r['cache_hits_warm_pass']}/{w['prompts']}", ""]
    if r["savings"]:
        s = r["savings"]
        L.append(f"Cost: baseline ${s['baseline_usd']:.6f} vs routed ${s['routed_usd']:.6f} ({s['saved_pct']:.1f}% saved), "
                 "computed from config/prices.yaml and the token counts above.")
    else:
        L.append("Cost: **not computed** — `config/prices.yaml` still has placeholder prices. "
                 "Token counts above are measured; fill in the prices to get dollar figures.")
    L += ["", "| task | prompts | baseline correct | routed correct | routed final tier |", "|---|---|---|---|---|"]
    for t, v in r["by_task"].items():
        L.append(f"| {t} | {v['prompts']} | {v['baseline_correct']} | {v['routed_correct']} | {v['final_tier']} |")
    L += ["", "<details><summary>Per prompt</summary>", "", "| id | task | baseline | routed | final tier | escalated | warm hit |", "|---|---|---|---|---|---|---|"]
    for p in r["per_prompt"]:
        L.append(f"| {p['id']} | {p['task']} | {'✓' if p['baseline_correct'] else '✗'} | {'✓' if p['routed_correct'] else '✗'} | "
                 f"{p['final_tier']} | {'yes' if p['escalated'] else ''} | {'✓' if p['warm_cache_hit'] else ''} |")
    L += ["", "</details>", ""]
    return "\n".join(L)
