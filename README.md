# Sornaris

**`git bisect` for LLM-agent regressions.** When your agent's success rate
drops, `sornaris` binary-searches *which* change broke it — a prompt edit, a
silent model upgrade, a tool-schema diff, or a RAG-corpus refresh — in
`log₂(N)` eval runs instead of `N`.

[![CI](https://github.com/Sergiipis/sornaris/actions/workflows/ci.yml/badge.svg)](https://github.com/Sergiipis/sornaris/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sornaris.svg)](https://pypi.org/project/sornaris/)
[![Python](https://img.shields.io/pypi/pyversions/sornaris.svg)](https://pypi.org/project/sornaris/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/Sergiipis/sornaris/badge)](https://scorecard.dev/viewer/?uri=github.com/Sergiipis/sornaris)

## Why this matters

Every eval framework can tell you *that* your agent regressed. None tell you
*which* of the many things you changed last week caused it. Real agents move on
four axes at once — the prompt, the model, the tool schema, and the retrieval
corpus — and bisecting them by hand means re-running your eval set over and
over. `sornaris` does the binary search for you and names the culprit version.

Zero runtime dependencies — pure standard library (with an optional sqlite
response cache). Bring your own provider, or use the built-in OpenAI / Anthropic
adapters (stdlib `urllib`, API key from the environment).

## Install

```bash
pip install sornaris
```

## Quickstart (offline, no API key)

```python
import re

from sornaris import (
    BaseProvider,
    EvalExample,
    ExactMatchScorer,
    ModelVersion,
    PromptVersion,
    bisect_single_axis,
    run_eval,
)

# Eight prompt versions in time order; a regression was introduced at v5.
prompts = [
    PromptVersion(version_id=f"v{i}", content=f"build {i}: answer the user")
    for i in range(8)
]
examples = [EvalExample(example_id=f"e{i}", input=f"q{i}", expected="ok") for i in range(5)]


class DemoProvider(BaseProvider):  # stand-in for a real LLM call
    def generate(self, prompt: str, model_id: str) -> str:
        build = int(re.search(r"build (\d+)", prompt).group(1))
        return "ok" if build < 5 else "BROKEN"  # broke at build 5


model, provider, scorer = ModelVersion(model_id="demo"), DemoProvider(), ExactMatchScorer()


def evaluate(pv):
    _, mean = run_eval(pv, model, examples, provider, scorer)
    return mean


report = bisect_single_axis(prompts, evaluate, baseline_idx=0, current_idx=7, threshold=0.5)
print(report.version_id)     # -> "v5"
print(len(report.steps))     # -> ~3 probe rounds, not 8
```

Runnable versions (single-axis and multi-axis) live in [`examples/`](examples/).

## CLI

Bisect prompt versions against a **real** model (the provider reads its key from
the environment):

```bash
export OPENAI_API_KEY=sk-...
sornaris run \
  --prompts examples/prompt_versions.jsonl \
  --evals examples/eval.jsonl \
  --provider openai \
  --model-id gpt-4o-mini \
  --scorer contains \
  --threshold 0.75 \
  --report bisect_report.json
```

- `--provider` — `fake` (offline, for wiring checks), `openai`, or `anthropic`.
- `--scorer` — `exact` or `contains`.
- `--cache PATH` — sqlite response cache; repeated runs over the same eval set
  get cheaper.
- `--models models.jsonl` — also bisect the **model** axis (prompt + model).

`prompts` / `models` / `evals` are JSONL, one object per line:

```jsonc
// versions.jsonl
{"version_id": "v1", "content": "Be concise.", "parent_id": null, "timestamp": 1.0}
// models.jsonl
{"model_id": "gpt-4o-mini", "provider": "openai"}
// eval.jsonl
{"example_id": "e1", "input": "what is 2+2?", "expected": "4"}
```

## How it works

A regression introduced somewhere in an ordered list of `N` versions is, by
definition, monotonic: it's good before the culprit and bad from the culprit on.
That's exactly the precondition for binary search, so `sornaris` localizes it
in `log₂(N)` evaluations. The multi-axis orchestrator pins every other axis at
its latest value and walks one axis at a time — so it can say "the model axis is
the cause, the prompt axis is innocent." With the sqlite cache, repeated bisects
on the same eval set reuse prior scores.

> Multi-axis is deliberately a one-axis-at-a-time search (other axes pinned at
> current), not a full grid — it finds the single axis that, rolled back,
> recovers the score. That covers the common "what did I change?" case cheaply.

## Modules

- `models` — value objects: `PromptVersion`, `ModelVersion`, `EvalExample`,
  `EvalResult`, `BisectStep`, `BisectReport`, `AxisType`.
- `scoring` — `ExactMatchScorer`, `ContainsScorer`, `RegexScorer`, `CallableScorer`.
- `cache` — `BisectCache` (sqlite-backed, on-disk or in-memory).
- `providers` — `BaseProvider`, offline `FakeProvider` / `ScriptedProvider`, real
  `OpenAIProvider` / `AnthropicProvider`, and `build_provider(name, ...)`.
- `runner` — `run_eval(prompt, model, examples, provider, scorer, cache=None)`.
- `search` — `bisect_single_axis(versions, evaluate_fn, baseline_idx, current_idx, threshold)`.
- `multi` — `bisect_multi_axis(axes, evaluate_fn, threshold, priority=None)`.
- `cli` — the `sornaris` command-line entry point.

## Roadmap

- **v0.1** — single- and multi-axis bisect, OpenAI/Anthropic adapters, sqlite
  cache, CLI.
- **v0.2** — async providers, tool-schema and RAG-corpus axes wired into the
  CLI, richer scorers (LLM-judge), JSON-schema for reports.
- **v1.0** — hosted dashboard (track regressions over time), CI action, and
  optional signed bisect reports.

## Verifying a release

Every release is built and signed in CI via PyPI Trusted Publishing — no
long-lived tokens, no hand-uploaded files. You can confirm an artifact is exactly
what the workflow produced:

```bash
# 1. PyPI provenance (PEP 740 attestations) — shown on the project's PyPI page;
#    pip verifies attestations automatically on install (pip >= 24.1).
pip install sornaris

# 2. Sigstore signatures — each wheel/sdist is signed (keyless, OIDC) and the
#    .sigstore.json bundles are attached to the GitHub Release. Verify with:
python -m pip install sigstore
python -m sigstore verify identity \
  --cert-identity "https://github.com/Sergiipis/sornaris/.github/workflows/publish.yml@refs/tags/v0.1.0" \
  --cert-oidc-issuer "https://token.actions.githubusercontent.com" \
  sornaris-0.1.0-py3-none-any.whl

# 3. Checksums — SHA256SUMS is attached to each GitHub Release.
sha256sum -c SHA256SUMS
```

A CycloneDX SBOM (`sbom.cdx.json` / `.xml`) is attached to every release.
Builds set `SOURCE_DATE_EPOCH` from the tag commit, so the wheel is reproducible.

## License

MIT — see [LICENSE](LICENSE). Free for any use, including commercial.

For paid consulting, custom features or integrations, contact
[@Sergiipis on GitHub](https://github.com/Sergiipis).
