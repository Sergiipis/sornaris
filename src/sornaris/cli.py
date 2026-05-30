"""CLI entry point for sornaris."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from sornaris.cache import BisectCache
from sornaris.models import EvalExample, ModelVersion, PromptVersion
from sornaris.multi import bisect_multi_axis
from sornaris.providers import ProviderError, build_provider
from sornaris.runner import run_eval
from sornaris.scoring import ContainsScorer, ExactMatchScorer
from sornaris.search import bisect_single_axis


def load_prompts_jsonl(path: str) -> list:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(
                PromptVersion(
                    version_id=d["version_id"],
                    content=d["content"],
                    parent_id=d.get("parent_id"),
                    timestamp=d.get("timestamp", 0.0),
                )
            )
    return out


def load_evals_jsonl(path: str) -> list:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(
                EvalExample(
                    example_id=d["example_id"],
                    input=d["input"],
                    expected=d.get("expected"),
                    metadata=d.get("metadata"),
                )
            )
    return out


def load_models_jsonl(path: str) -> list:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(
                ModelVersion(
                    model_id=d["model_id"],
                    provider=d.get("provider"),
                    version=d.get("version"),
                )
            )
    return out


def build_scorer(name: str):
    if name == "contains":
        return ContainsScorer()
    return ExactMatchScorer()


def report_to_dict(report) -> dict:
    steps = []
    for s in report.steps or []:
        steps.append(
            {
                "step_index": s.step_index,
                "axis": s.axis,
                "low_idx": s.low_idx,
                "high_idx": s.high_idx,
                "probed_idx": s.probed_idx,
                "probed_score": float(s.probed_score),
                "decision": s.decision,
            }
        )
    return {
        "found": bool(report.found),
        "axis": report.axis,
        "version_id": report.version_id,
        "baseline_score": float(report.baseline_score),
        "regressed_score": float(report.regressed_score),
        "steps": steps,
    }


def reports_to_dict(reports: dict) -> dict:
    """Serialize a multi-axis ``{axis_name: BisectReport}`` mapping."""
    return {axis: report_to_dict(rep) for axis, rep in reports.items()}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sornaris",
        description="Binary-search which change introduced an LLM-agent regression.",
    )
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser(
        "run",
        help="Bisect prompt versions (and optionally model versions) to find the culprit",
    )
    run_p.add_argument("--prompts", required=True, help="JSONL of prompt versions (oldest first)")
    run_p.add_argument("--evals", required=True, help="JSONL of eval examples")
    run_p.add_argument(
        "--models",
        default=None,
        help="optional JSONL of model versions; if given, bisects prompt AND model axes",
    )
    run_p.add_argument(
        "--provider",
        default="fake",
        choices=["fake", "openai", "anthropic"],
        help="LLM provider (real providers read the API key from the environment)",
    )
    run_p.add_argument(
        "--model-id",
        default="fake-model",
        help="model id for single-axis runs / default model for the provider",
    )
    run_p.add_argument("--scorer", default="exact", choices=["exact", "contains"])
    run_p.add_argument("--threshold", type=float, default=0.5)
    run_p.add_argument("--cache", default=None, help="optional sqlite cache path to reuse scores")
    run_p.add_argument("--report", default=None, help="optional path to also write the JSON report")
    return parser


def _emit(payload: dict, report_path: Optional[str]) -> None:
    rendered = json.dumps(payload, indent=2)
    print(rendered)
    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(rendered)


def main(argv: Optional[list] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.command != "run":
        parser.print_help(sys.stderr)
        return 2

    try:
        prompts = load_prompts_jsonl(args.prompts)
    except FileNotFoundError:
        print(f"prompts file not found: {args.prompts}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"failed to load prompts: {e}", file=sys.stderr)
        return 3

    try:
        examples = load_evals_jsonl(args.evals)
    except FileNotFoundError:
        print(f"evals file not found: {args.evals}", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"failed to load evals: {e}", file=sys.stderr)
        return 4

    if len(prompts) < 2:
        print("need at least 2 prompt versions to bisect", file=sys.stderr)
        return 5

    models = None
    if args.models is not None:
        try:
            models = load_models_jsonl(args.models)
        except FileNotFoundError:
            print(f"models file not found: {args.models}", file=sys.stderr)
            return 4
        except Exception as e:
            print(f"failed to load models: {e}", file=sys.stderr)
            return 4
        if len(models) < 2:
            print("need at least 2 model versions for the model axis", file=sys.stderr)
            return 5

    try:
        provider = build_provider(args.provider, model_id=args.model_id)
    except ProviderError as e:
        print(f"provider error: {e}", file=sys.stderr)
        return 6

    scorer = build_scorer(args.scorer)
    cache = BisectCache(args.cache) if args.cache else None

    try:
        if models is None:
            # Single-axis: bisect prompt versions, model pinned to --model-id.
            model_version = ModelVersion(model_id=args.model_id)

            def evaluate_fn(pv):
                _, mean = run_eval(pv, model_version, examples, provider, scorer, cache=cache)
                return mean

            report = bisect_single_axis(
                prompts,
                evaluate_fn,
                baseline_idx=0,
                current_idx=len(prompts) - 1,
                threshold=args.threshold,
                axis="prompt",
            )
            _emit(report_to_dict(report), args.report)
        else:
            # Multi-axis: bisect prompt AND model axes (prompt first by priority).
            axes = {
                "prompt": {"versions": prompts, "baseline_idx": 0, "current_idx": len(prompts) - 1},
                "model": {"versions": models, "baseline_idx": 0, "current_idx": len(models) - 1},
            }

            def evaluate_probe(probe):
                _, mean = run_eval(
                    probe["prompt"], probe["model"], examples, provider, scorer, cache=cache
                )
                return mean

            reports = bisect_multi_axis(
                axes, evaluate_probe, threshold=args.threshold, priority=["prompt", "model"]
            )
            _emit(reports_to_dict(reports), args.report)
    except ProviderError as e:
        print(f"provider error during eval: {e}", file=sys.stderr)
        return 6
    finally:
        if cache is not None:
            cache.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
