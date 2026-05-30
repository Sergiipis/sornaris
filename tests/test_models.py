from sornaris.models import (
    AxisType,
    PromptVersion,
    ModelVersion,
    EvalExample,
    EvalResult,
    BisectStep,
    BisectReport,
    prompt_version_hash,
)


def test_axis_type_string_values():
    assert AxisType.PROMPT == "prompt"
    assert AxisType.MODEL == "model"
    assert AxisType.TOOL_SCHEMA == "tool_schema"
    assert AxisType.RAG_CORPUS == "rag_corpus"


def test_prompt_version_defaults():
    pv = PromptVersion(version_id="v1", content="hello")
    assert pv.parent_id is None
    assert pv.timestamp == 0.0


def test_model_version_defaults():
    mv = ModelVersion(model_id="gpt-4")
    assert mv.provider is None
    assert mv.version is None


def test_eval_example_defaults():
    ex = EvalExample(example_id="e1", input="what is 2+2?")
    assert ex.expected is None
    assert ex.metadata is None


def test_eval_result_defaults():
    r = EvalResult(example_id="e1", output="4", score=1.0)
    assert r.latency_s == 0.0


def test_bisect_step_construct():
    s = BisectStep(
        step_index=0,
        axis="prompt",
        low_idx=0,
        high_idx=10,
        probed_idx=5,
        probed_score=0.7,
        decision="go_left",
    )
    assert s.decision == "go_left"
    assert s.probed_idx == 5


def test_bisect_report_construct():
    rep = BisectReport(
        found=True,
        axis="prompt",
        version_id="v5",
        baseline_score=0.95,
        regressed_score=0.5,
        steps=[],
    )
    assert rep.found is True
    assert rep.examples_failed is None


def test_prompt_version_hash_deterministic():
    pv1 = PromptVersion(version_id="a", content="hello", parent_id="root")
    pv2 = PromptVersion(version_id="b", content="hello", parent_id="root")
    assert prompt_version_hash(pv1) == prompt_version_hash(pv2)


def test_prompt_version_hash_changes_with_content():
    pv1 = PromptVersion(version_id="a", content="hello")
    pv2 = PromptVersion(version_id="a", content="world")
    assert prompt_version_hash(pv1) != prompt_version_hash(pv2)


def test_prompt_version_hash_changes_with_parent():
    pv1 = PromptVersion(version_id="a", content="same", parent_id="p1")
    pv2 = PromptVersion(version_id="a", content="same", parent_id="p2")
    assert prompt_version_hash(pv1) != prompt_version_hash(pv2)


def test_prompt_version_hash_no_parent_is_empty_string():
    pv1 = PromptVersion(version_id="a", content="x", parent_id=None)
    pv2 = PromptVersion(version_id="a", content="x", parent_id="")
    assert prompt_version_hash(pv1) == prompt_version_hash(pv2)


def test_prompt_version_hash_length_is_64():
    pv = PromptVersion(version_id="a", content="anything")
    assert len(prompt_version_hash(pv)) == 64
