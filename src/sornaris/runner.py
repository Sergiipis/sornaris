"""Eval runner: evaluates (prompt_version, model_version) pair on a list of examples."""

from __future__ import annotations

from sornaris.cache import make_cache_key
from sornaris.models import (
    EvalExample,
    EvalResult,
    ModelVersion,
    PromptVersion,
    prompt_version_hash,
)
from sornaris.scoring import aggregate_mean

# Re-exported for backwards compatibility: callers/tests reference these as
# attributes of `sornaris.runner` (the canonical definitions live in models).
__all__ = [
    "PromptVersion",
    "ModelVersion",
    "EvalExample",
    "EvalResult",
    "prompt_version_hash",
    "make_cache_key",
    "aggregate_mean",
    "run_eval",
]


def run_eval(
    prompt_version,
    model_version,
    examples: list,
    provider,
    scorer,
    cache=None,
    prompt_template: str = "{prompt}\n\nInput: {input}",
) -> tuple:
    results = []
    prompt_hash = prompt_version_hash(prompt_version)

    for example in examples:
        cache_key = make_cache_key(prompt_hash, model_version.model_id, example.example_id)
        if cache is not None and cache.has(cache_key):
            cached_score = cache.get(cache_key)
            results.append(
                EvalResult(
                    example_id=example.example_id,
                    output="__cached__",
                    score=cached_score,
                    latency_s=0.0,
                )
            )
        else:
            rendered = prompt_template.format(prompt=prompt_version.content, input=example.input)
            output = provider.generate(rendered, model_version.model_id)
            score = scorer.score(output, example.expected)
            if cache is not None:
                cache.set(cache_key, score)
            results.append(
                EvalResult(
                    example_id=example.example_id,
                    output=output,
                    score=score,
                    latency_s=0.0,
                )
            )

    mean_score = aggregate_mean([r.score for r in results])
    return results, mean_score
