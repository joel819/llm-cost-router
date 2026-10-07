from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import usage as usage_log
from .cache import Cache, CacheEntry, cache_key, connect
from .checks.base import CheckOutcome
from .checks.exact import ExactCheck
from .checks.json_schema import JsonSchemaCheck
from .checks.judge import JudgeCheck
from .config import Config, Task, Tier
from .cost import PriceBook, Usage
from .errors import MissingPriceError, ProviderError


@dataclass
class Attempt:
    tier: str
    model: str
    passed: bool
    reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    judge_input_tokens: int = 0
    judge_output_tokens: int = 0
    error: str | None = None


@dataclass
class Result:
    text: str
    tier: str | None
    model: str | None
    cached: bool
    passed: bool                              # did the final answer pass its quality check?
    attempts: list[Attempt] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float | None = None                 # USD from config/prices.yaml, or None if a price is missing
    cost_note: str | None = None
    latency_ms: int = 0

    def to_dict(self) -> dict:
        return {"text": self.text, "tier": self.tier, "model": self.model, "cached": self.cached, "passed": self.passed,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens, "cost_usd": self.cost,
                "cost_note": self.cost_note, "latency_ms": self.latency_ms,
                "attempts": [a.__dict__ for a in self.attempts]}


class Router:
    def __init__(self, cfg: Config, provider, db_path: str = ":memory:", *, strict_costs: bool = False,
                 use_cache: bool = True):
        self.cfg, self.provider, self.strict_costs, self.use_cache = cfg, provider, strict_costs, use_cache
        self.conn = connect(db_path)
        self.cache = Cache(self.conn)
        self.prices = PriceBook(cfg.price_table)

    # -- checks ------------------------------------------------------------------
    def _check_for(self, task: Task, tier: Tier):
        if task.check == "exact":
            return ExactCheck(task.allowed)
        if task.check == "json_schema":
            return JsonSchemaCheck(task.schema)
        return JudgeCheck(self.provider, self.cfg.strongest, task.rubric)

    # -- main entry ------------------------------------------------------------------
    def complete(self, prompt: str, task_type: str, expected: str | None = None) -> Result:
        t0 = time.perf_counter()
        task = self.cfg.task(task_type)
        key = cache_key(prompt + (f"\n#expected={expected}" if expected is not None else ""), task_type)

        if self.use_cache and (hit := self.cache.get(key)):
            res = Result(hit.text, hit.tier, hit.model, True, True, cost=0.0, cost_note="cache hit",
                         latency_ms=int((time.perf_counter() - t0) * 1000))
            self._log(res, task_type, key)
            return res

        attempts: list[Attempt] = []
        final: tuple[str, Tier, bool] | None = None
        spent: list[tuple[Tier, Usage]] = []          # every billable call, for cost
        last_idx = len(self.cfg.tiers) - 1

        for i, tier in enumerate(self.cfg.tiers):
            try:
                reply = self.provider.chat(tier, task.system, prompt, task.max_tokens)
            except ProviderError as exc:
                attempts.append(Attempt(tier.name, tier.model, False, "provider error", error=str(exc)[:300]))
                if i == last_idx and final is None:
                    raise
                continue
            spent.append((tier, reply.usage))
            if task.check == "judge" and i == last_idx:
                # Nothing above the strongest tier to escalate to, and it is its own judge: accept as-is.
                outcome = CheckOutcome(True, "strongest tier — not self-judged")
            else:
                try:
                    outcome = self._check_for(task, tier).evaluate(prompt, reply.text, expected)
                except ProviderError as exc:
                    outcome = CheckOutcome(False, f"judge unavailable: {str(exc)[:120]}")
                if outcome.usage.input_tokens or outcome.usage.output_tokens:
                    spent.append((self.cfg.strongest, outcome.usage))
            attempts.append(Attempt(tier.name, tier.model, outcome.passed, outcome.reason, reply.usage.input_tokens,
                                    reply.usage.output_tokens, outcome.usage.input_tokens, outcome.usage.output_tokens))
            final = (reply.text, tier, outcome.passed)
            if outcome.passed:
                break

        if final is None:
            raise ProviderError("no tier produced an answer")
        text, tier, passed = final
        total = Usage()
        for _, u in spent:
            total += u
        cost, note = self._cost(spent)
        res = Result(text, tier.name, tier.model, False, passed, attempts, total.input_tokens, total.output_tokens,
                     cost, note, int((time.perf_counter() - t0) * 1000))
        if passed and self.use_cache:
            self.cache.put(key, task_type, CacheEntry(text, tier.name, tier.model))
        self._log(res, task_type, key)
        return res

    def _cost(self, spent: list[tuple[Tier, Usage]]) -> tuple[float | None, str | None]:
        total = 0.0
        try:
            for tier, u in spent:
                total += self.prices.cost(tier.price_key, u)
        except MissingPriceError as exc:
            if self.strict_costs:
                raise
            return None, str(exc)
        return total, None

    def _log(self, r: Result, task: str, key: str) -> None:
        usage_log.log_request(self.conn, task=task, key=key, tier=r.tier, model=r.model, cached=r.cached, passed=r.passed,
                              attempts=[a.__dict__ for a in r.attempts], input_tokens=r.input_tokens,
                              output_tokens=r.output_tokens, cost=r.cost, cost_note=r.cost_note, latency_ms=r.latency_ms)
