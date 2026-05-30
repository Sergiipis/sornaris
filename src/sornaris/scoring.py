"""Scoring strategies for eval outputs."""

from __future__ import annotations

import re
from typing import Callable, Optional


class ExactMatchScorer:
    def __init__(self, case_sensitive: bool = True) -> None:
        self.case_sensitive = case_sensitive

    def score(self, output: str, expected: Optional[str]) -> float:
        if expected is None:
            return 0.0
        if self.case_sensitive:
            return 1.0 if output == expected else 0.0
        return 1.0 if output.lower() == expected.lower() else 0.0


class ContainsScorer:
    def __init__(self, case_sensitive: bool = True) -> None:
        self.case_sensitive = case_sensitive

    def score(self, output: str, expected: Optional[str]) -> float:
        if expected is None or expected == "":
            return 0.0
        if self.case_sensitive:
            return 1.0 if expected in output else 0.0
        return 1.0 if expected.lower() in output.lower() else 0.0


class RegexScorer:
    def __init__(self, pattern: str, flags: int = 0) -> None:
        self._compiled = re.compile(pattern, flags)

    def score(self, output: str, expected: Optional[str] = None) -> float:
        return 1.0 if self._compiled.search(output) is not None else 0.0


class CallableScorer:
    def __init__(self, fn: Callable[[str, Optional[str]], float]) -> None:
        self._fn = fn

    def score(self, output: str, expected: Optional[str]) -> float:
        raw = float(self._fn(output, expected))
        if raw < 0.0:
            return 0.0
        if raw > 1.0:
            return 1.0
        return raw


def aggregate_mean(scores: list) -> float:
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def aggregate_pass_rate(scores: list, threshold: float = 0.5) -> float:
    if not scores:
        return 0.0
    passed = sum(1 for s in scores if s >= threshold)
    return passed / len(scores)
