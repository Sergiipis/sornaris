"""Example 2 — multi-axis bisect: blame the model, exonerate the prompt.

A realistic situation: your agent regressed, and you changed BOTH the prompt
and the model around the same time. Which one broke it?

Here the prompt is innocent (it never affects correctness) and the regression
is a silent model upgrade: model builds >= 3 are broken. ``bisect_multi_axis``
pins every axis at its latest value and walks each axis back independently:

* the **model** axis recovers when rolled back  -> culprit found at model-build-3
* the **prompt** axis never recovers (the bad model is still pinned) -> not the cause

Fully offline, no API key. Run:
    python examples/02_multi_axis.py
"""

from __future__ import annotations

import re

from sornaris import (
    BaseProvider,
    EvalExample,
    ExactMatchScorer,
    ModelVersion,
    PromptVersion,
    bisect_multi_axis,
    run_eval,
)

CULPRIT_MODEL_BUILD = 3


class ModelRegressionProvider(BaseProvider):
    """Offline LLM stand-in whose correctness depends only on the model build."""

    def __init__(self, culprit_build: int) -> None:
        self.culprit_build = culprit_build

    def generate(self, prompt: str, model_id: str) -> str:
        match = re.search(r"build-(\d+)", model_id)
        build = int(match.group(1)) if match else 0
        return "ok" if build < self.culprit_build else "BROKEN"


def main() -> int:
    prompts = [PromptVersion(version_id=f"p{i}", content=f"prompt revision {i}") for i in range(4)]
    models = [ModelVersion(model_id=f"model-build-{i}") for i in range(6)]
    examples = [
        EvalExample(example_id=f"e{i}", input=f"question {i}", expected="ok") for i in range(5)
    ]
    provider = ModelRegressionProvider(culprit_build=CULPRIT_MODEL_BUILD)
    scorer = ExactMatchScorer()

    axes = {
        "prompt": {"versions": prompts, "baseline_idx": 0, "current_idx": len(prompts) - 1},
        "model": {"versions": models, "baseline_idx": 0, "current_idx": len(models) - 1},
    }

    def evaluate_probe(probe: dict) -> float:
        _, mean = run_eval(probe["prompt"], probe["model"], examples, provider, scorer)
        return mean

    reports = bisect_multi_axis(axes, evaluate_probe, threshold=0.5, priority=["prompt", "model"])

    for axis, report in reports.items():
        verdict = f"culprit = {report.version_id}" if report.found else "not the cause"
        print(f"{axis:7s}: found={report.found!s:5s}  {verdict}")

    expected = f"model-build-{CULPRIT_MODEL_BUILD}"
    assert reports["model"].found, "model axis should localize the regression"
    assert reports["model"].version_id == expected, (
        f"expected {expected}, got {reports['model'].version_id}"
    )
    assert not reports["prompt"].found, "prompt axis should be exonerated"
    print(f"\nOK — blamed the model ({expected}); prompt axis cleared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
