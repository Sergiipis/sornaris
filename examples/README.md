# Examples

All Python examples are **offline and deterministic** — no API key required —
so they double as runnable smoke tests.

## 1. Find a prompt regression (`01_find_prompt_regression.py`)

Eight prompt versions; a regression was introduced at `v5`. A tiny offline
provider encodes that behaviour and `bisect_single_axis` isolates the culprit
in `log₂(8) ≈ 3` probe rounds instead of scanning all eight.

```bash
python examples/01_find_prompt_regression.py
```

Expected output ends with:

```
OK — correctly isolated the regression to v5.
```

## 2. Multi-axis bisect (`02_multi_axis.py`)

You changed both the prompt and the model. The prompt is innocent; a silent
model upgrade (`model-build-3`) is the real cause. `bisect_multi_axis` walks
each axis back independently, blames the model and exonerates the prompt.

```bash
python examples/02_multi_axis.py
```

## 3. The CLI against a real model

`prompt_versions.jsonl` (six increasingly terse system prompts — the last two
"answer with an emoji" versions break the eval) and `eval.jsonl` (four
factual questions) let you bisect a **real** model. The `contains` scorer
passes when the expected answer appears anywhere in the output.

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

Anthropic works the same way with `--provider anthropic --model-id claude-...`
and `ANTHROPIC_API_KEY`. Add `--models models.jsonl` to bisect the prompt and
model axes together.

> The offline `--provider fake` is for wiring/structure checks only — its
> hash-style output never matches an expected answer, so it won't surface a
> real regression. Use a real provider (or the Python examples above) to see
> a culprit isolated.
