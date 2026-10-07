from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .errors import ConfigError


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key_env: str

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env) or None


@dataclass(frozen=True)
class Tier:
    name: str
    provider: str
    model: str
    params: dict = field(default_factory=dict)

    @property
    def price_key(self) -> str:
        return f"{self.provider}/{self.model}"


@dataclass(frozen=True)
class Task:
    name: str
    system: str
    check: str
    max_tokens: int = 500
    allowed: tuple[str, ...] = ()
    schema: dict | None = None
    rubric: str = ""


@dataclass
class Config:
    providers: dict[str, Provider]
    tiers: list[Tier]
    tasks: dict[str, Task]
    price_table: dict
    min_interval: float = 0.0

    @property
    def strongest(self) -> Tier:
        return self.tiers[-1]

    def task(self, name: str) -> Task:
        if name not in self.tasks:
            raise ConfigError(f"unknown task type {name!r}; configured: {sorted(self.tasks)}")
        return self.tasks[name]


def _read(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    return yaml.safe_load(path.read_text()) or {}


def load_config(config_dir: str | Path = "config") -> Config:
    d = Path(config_dir)
    t, p, k = _read(d / "tiers.yaml"), _read(d / "prices.yaml"), _read(d / "tasks.yaml")

    providers = {n: Provider(n, v["base_url"].rstrip("/"), v["api_key_env"]) for n, v in (t.get("providers") or {}).items()}
    tiers = [Tier(x["name"], x["provider"], x["model"], dict(x.get("params") or {})) for x in t.get("tiers") or []]
    if len(tiers) < 1:
        raise ConfigError("tiers.yaml must define at least one tier (cheapest first)")
    for x in tiers:
        if x.provider not in providers:
            raise ConfigError(f"tier {x.name!r} uses unknown provider {x.provider!r}")
    if len({x.name for x in tiers}) != len(tiers):
        raise ConfigError("tier names must be unique")

    tasks = {}
    for name, v in (k.get("tasks") or {}).items():
        if v.get("check") not in {"exact", "json_schema", "judge"}:
            raise ConfigError(f"task {name!r}: check must be exact, json_schema or judge")
        tasks[name] = Task(name, v["system"].strip(), v["check"], int(v.get("max_tokens", 500)),
                           tuple(str(a).lower() for a in v.get("allowed") or ()), v.get("schema"), (v.get("rubric") or "").strip())
    if not tasks:
        raise ConfigError("tasks.yaml defines no tasks")
    return Config(providers, tiers, tasks, p.get("models") or {}, float(t.get("min_interval_seconds") or 0))
