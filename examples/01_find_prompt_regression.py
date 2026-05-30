"""Example 1 — localize a prompt regression, fully offline.

We simulate eight prompt versions where a regression was introduced at v5:
versions v0..v4 answer correctly, v5..v7 are broken. A small offline provider
encodes that behaviour (it reads the build number embedded in the prompt), so
the example needs no API key and is deterministic.

``bisect_single_axis`` then finds the exact culprit (v5) in log2(8) ≈ 3 probe
rounds instead of scanning all eight versions.

Run:
    python examples/01_find_prompt_regression.py
"""

from __future__ import annotations

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

CULPRIT_INDEX = 5
N_VERSIONS = 8


class RegressionDemoProvider(BaseProvider):
    """Offline stand-in for a real LLM.

    Returns the correct answer ("ok") for prompt builds before the culprit and
    a broken answer afterwards — a synthetic, reproducible regression.
    """

    def __init__(self, culprit_index: int) -> None:
        self.culprit_index = culprit_index

    def generate(self, prompt: str, model_id: str) -> str:
        match = re.search(r"build (\d+)", prompt)
        build = int(match.group(1)) if match else 0
        return "ok" if build < self.culprit_index else "BROKEN"


def main() -> int:
    prompts = [
        PromptVersion(version_id=f"v{i}", content=f"build {i}: answer the user.")
        for i in range(N_VERSIONS)
    ]
    examples = [
        EvalExample(example_id=f"e{i}", input=f"question {i}", expected="ok") for i in range(5)
    ]
    model = ModelVersion(model_id="demo-model")
    provider = RegressionDemoProvider(culprit_index=CULPRIT_INDEX)
    scorer = ExactMatchScorer()

    def evaluate(prompt_version: PromptVersion) -> float:
        _, mean = run_eval(prompt_version, model, examples, provider, scorer)
        return mean

    report = bisect_single_axis(
        prompts,
        evaluate,
        baseline_idx=0,
        current_idx=N_VERSIONS - 1,
        threshold=0.5,
    )

    print(f"regression found: {report.found}")
    print(f"culprit version:  {report.version_id}")
    print(f"baseline score:   {report.baseline_score:.2f}")
    print(f"regressed score:  {report.regressed_score:.2f}")
    print(f"probe rounds:     {len(report.steps)} (vs {N_VERSIONS} for a linear scan)")

    expected = f"v{CULPRIT_INDEX}"
    assert report.found, "expected to find a regression"
    assert report.version_id == expected, f"expected culprit {expected}, got {report.version_id}"
    print(f"\nOK — correctly isolated the regression to {expected}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
