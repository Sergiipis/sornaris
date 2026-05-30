"""Core dataclasses and enums for sornaris engine."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AxisType(str, Enum):
    PROMPT = "prompt"
    MODEL = "model"
    TOOL_SCHEMA = "tool_schema"
    RAG_CORPUS = "rag_corpus"


@dataclass
class PromptVersion:
    version_id: str
    content: str
    parent_id: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class ModelVersion:
    model_id: str
    provider: Optional[str] = None
    version: Optional[str] = None


@dataclass
class EvalExample:
    example_id: str
    input: str
    expected: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class EvalResult:
    example_id: str
    output: str
    score: float
    latency_s: float = 0.0


@dataclass
class BisectStep:
    step_index: int
    axis: str
    low_idx: int
    high_idx: int
    probed_idx: int
    probed_score: float
    decision: str


@dataclass
class BisectReport:
    found: bool
    axis: str
    version_id: Optional[str]
    baseline_score: float
    regressed_score: float
    steps: list
    examples_failed: Optional[list] = None


def prompt_version_hash(pv: PromptVersion) -> str:
    payload = (pv.content + "|" + (pv.parent_id or "")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
