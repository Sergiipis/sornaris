"""Single-axis binary bisect: find first version where score drops below threshold."""

from __future__ import annotations

from sornaris.models import BisectReport, BisectStep


def _version_label(v) -> str:
    if hasattr(v, "version_id"):
        return v.version_id
    if hasattr(v, "model_id"):
        return v.model_id
    return str(v)


def bisect_single_axis(
    versions: list,
    evaluate_fn,
    baseline_idx: int,
    current_idx: int,
    threshold: float,
    axis: str = "prompt",
):
    baseline_score = evaluate_fn(versions[baseline_idx])
    current_score = evaluate_fn(versions[current_idx])

    if baseline_score < threshold:
        return BisectReport(
            found=False,
            axis=axis,
            version_id=None,
            baseline_score=baseline_score,
            regressed_score=current_score,
            steps=[],
        )
    if current_score >= threshold:
        return BisectReport(
            found=False,
            axis=axis,
            version_id=None,
            baseline_score=baseline_score,
            regressed_score=current_score,
            steps=[],
        )

    low = baseline_idx
    high = current_idx
    steps: list = []
    step_index = 0

    while high - low > 1:
        mid = (low + high) // 2
        probed_score = evaluate_fn(versions[mid])
        if probed_score >= threshold:
            decision = "go_right"
            low = mid
        else:
            decision = "go_left"
            high = mid
        steps.append(
            BisectStep(
                step_index=step_index,
                axis=axis,
                low_idx=low,
                high_idx=high,
                probed_idx=mid,
                probed_score=probed_score,
                decision=decision,
            )
        )
        step_index += 1

    found_idx = high
    # Reuse current_score if found_idx == current_idx to avoid duplicate eval
    final_score = current_score if found_idx == current_idx else evaluate_fn(versions[found_idx])
    steps.append(
        BisectStep(
            step_index=step_index,
            axis=axis,
            low_idx=low,
            high_idx=high,
            probed_idx=found_idx,
            probed_score=final_score,
            decision="found",
        )
    )

    return BisectReport(
        found=True,
        axis=axis,
        version_id=_version_label(versions[found_idx]),
        baseline_score=baseline_score,
        regressed_score=current_score,
        steps=steps,
    )
