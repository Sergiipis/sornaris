import re
import pytest
from sornaris.scoring import (
    ExactMatchScorer,
    ContainsScorer,
    RegexScorer,
    CallableScorer,
    aggregate_mean,
    aggregate_pass_rate,
)


def test_exact_match_case_sensitive_match():
    s = ExactMatchScorer()
    assert s.score("Hello", "Hello") == 1.0


def test_exact_match_case_sensitive_mismatch():
    s = ExactMatchScorer()
    assert s.score("Hello", "hello") == 0.0


def test_exact_match_case_insensitive():
    s = ExactMatchScorer(case_sensitive=False)
    assert s.score("Hello", "hello") == 1.0


def test_exact_match_none_expected():
    s = ExactMatchScorer()
    assert s.score("Hello", None) == 0.0


def test_contains_basic():
    s = ContainsScorer()
    assert s.score("the quick brown fox", "brown") == 1.0
    assert s.score("the quick brown fox", "purple") == 0.0


def test_contains_case_insensitive():
    s = ContainsScorer(case_sensitive=False)
    assert s.score("Hello World", "WORLD") == 1.0


def test_contains_none_or_empty_expected():
    s = ContainsScorer()
    assert s.score("anything", None) == 0.0
    assert s.score("anything", "") == 0.0


def test_regex_match():
    s = RegexScorer(r"\d+")
    assert s.score("found 42 items", None) == 1.0


def test_regex_no_match():
    s = RegexScorer(r"\d+")
    assert s.score("no numbers here", None) == 0.0


def test_regex_ignores_expected():
    s = RegexScorer(r"foo")
    assert s.score("foo bar", "completely ignored") == 1.0


def test_regex_flags():
    s = RegexScorer(r"foo", flags=re.IGNORECASE)
    assert s.score("FOO BAR", None) == 1.0


def test_callable_basic():
    s = CallableScorer(lambda out, exp: 0.7)
    assert s.score("x", "y") == 0.7


def test_callable_clamps_above_one():
    s = CallableScorer(lambda out, exp: 1.5)
    assert s.score("x", "y") == 1.0


def test_callable_clamps_below_zero():
    s = CallableScorer(lambda out, exp: -0.3)
    assert s.score("x", "y") == 0.0


def test_aggregate_mean_basic():
    assert aggregate_mean([1.0, 0.0, 0.5]) == pytest.approx(0.5)


def test_aggregate_mean_empty():
    assert aggregate_mean([]) == 0.0


def test_aggregate_pass_rate_basic():
    assert aggregate_pass_rate([1.0, 0.0, 1.0, 0.0], threshold=0.5) == 0.5


def test_aggregate_pass_rate_threshold_inclusive():
    assert aggregate_pass_rate([0.5, 0.5, 0.5], threshold=0.5) == 1.0


def test_aggregate_pass_rate_empty():
    assert aggregate_pass_rate([], threshold=0.5) == 0.0
