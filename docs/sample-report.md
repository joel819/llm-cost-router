# Benchmark report — 2026-10-07T12:18:26+00:00

Tiers (cheapest first): `groq/openai/gpt-oss-20b` → `groq/openai/gpt-oss-120b`
Baseline = every prompt sent to the strongest tier (`openai/gpt-oss-120b`).

| | prompts | correct (gold) | pass rate | input tokens | output tokens | cost |
|---|---|---|---|---|---|---|
| always strongest | 50 | 49 | 98% | 6321 | 1672 | not computed — fill in config/prices.yaml |
| routed (cold cache) | 50 | 49 | 98% | 9217 | 2409 | not computed — fill in config/prices.yaml |
| routed again (warm cache) | 50 | 49 | 98% | 0 | 0 | $0.000000 |

Routed final tier: {'small': 50} · escalations: 0 · cache hits on the second pass: 50/50

Cost: **not computed** — `config/prices.yaml` still has placeholder prices. Token counts above are measured; fill in the prices to get dollar figures.

| task | prompts | baseline correct | routed correct | routed final tier |
|---|---|---|---|---|
| classification | 17 | 16 | 16 | {'small': 17} |
| extraction | 17 | 17 | 17 | {'small': 17} |
| short_qa | 16 | 16 | 16 | {'small': 16} |

<details><summary>Per prompt</summary>

| id | task | baseline | routed | final tier | escalated | warm hit |
|---|---|---|---|---|---|---|
| cla-01 | classification | ✓ | ✓ | small |  | ✓ |
| cla-02 | classification | ✓ | ✓ | small |  | ✓ |
| cla-03 | classification | ✓ | ✓ | small |  | ✓ |
| cla-04 | classification | ✓ | ✓ | small |  | ✓ |
| cla-05 | classification | ✓ | ✓ | small |  | ✓ |
| cla-06 | classification | ✓ | ✗ | small |  | ✓ |
| cla-07 | classification | ✓ | ✓ | small |  | ✓ |
| cla-08 | classification | ✓ | ✓ | small |  | ✓ |
| cla-09 | classification | ✓ | ✓ | small |  | ✓ |
| cla-10 | classification | ✓ | ✓ | small |  | ✓ |
| cla-11 | classification | ✓ | ✓ | small |  | ✓ |
| cla-12 | classification | ✓ | ✓ | small |  | ✓ |
| cla-13 | classification | ✓ | ✓ | small |  | ✓ |
| cla-14 | classification | ✓ | ✓ | small |  | ✓ |
| cla-15 | classification | ✗ | ✓ | small |  | ✓ |
| cla-16 | classification | ✓ | ✓ | small |  | ✓ |
| cla-17 | classification | ✓ | ✓ | small |  | ✓ |
| ext-01 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-02 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-03 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-04 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-05 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-06 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-07 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-08 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-09 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-10 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-11 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-12 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-13 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-14 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-15 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-16 | extraction | ✓ | ✓ | small |  | ✓ |
| ext-17 | extraction | ✓ | ✓ | small |  | ✓ |
| sho-01 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-02 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-03 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-04 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-05 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-06 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-07 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-08 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-09 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-10 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-11 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-12 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-13 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-14 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-15 | short_qa | ✓ | ✓ | small |  | ✓ |
| sho-16 | short_qa | ✓ | ✓ | small |  | ✓ |

</details>
