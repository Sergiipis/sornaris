"""Multi-axis bisect: orchestrates single-axis bisects across N axes."""

from __future__ import annotations

from typing import Optional

from sornaris.search import bisect_single_axis


def bisect_multi_axis(
    axes: dict,
    evaluate_fn,
    threshold: float,
    priority: Optional[list] = None,
) -> dict:
    if not axes:
        return {}

    order = list(priority) if priority is not None else sorted(axes.keys())

    pinned = {
        axis_name: axes[axis_name]["versions"][axes[axis_name]["current_idx"]] for axis_name in axes
    }

    reports: dict = {}
    for axis_name in order:
        cfg = axes[axis_name]
        versions = cfg["versions"]
        baseline_idx = cfg["baseline_idx"]
        current_idx = cfg["current_idx"]

        def make_axis_eval(name):
            def axis_eval(v):
                probe = dict(pinned)
                probe[name] = v
                return evaluate_fn(probe)

            return axis_eval

        report = bisect_single_axis(
            versions,
            make_axis_eval(axis_name),
            baseline_idx,
            current_idx,
            threshold,
            axis=axis_name,
        )
        reports[axis_name] = report

    return reports
