import sornaris.search as bs

# 8 versions, regression starts at index 5: scores [1,1,1,1,1,0,0,0]
SCORES_REG_AT_5 = [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]


def test_finds_regression_at_index_5():
    versions = [f"v{i}" for i in range(8)]
    calls = []

    def eval_fn(v):
        idx = int(v[1:])
        calls.append(idx)
        return SCORES_REG_AT_5[idx]

    rep = bs.bisect_single_axis(versions, eval_fn, baseline_idx=0, current_idx=7, threshold=0.5)
    assert rep.found is True
    assert rep.version_id == "v5"
    assert rep.baseline_score == 1.0
    assert rep.regressed_score == 0.0


def test_no_regression_when_current_passes():
    versions = [f"v{i}" for i in range(5)]

    def eval_fn(v):
        return 1.0

    rep = bs.bisect_single_axis(versions, eval_fn, baseline_idx=0, current_idx=4, threshold=0.5)
    assert rep.found is False
    assert rep.version_id is None


def test_baseline_already_broken_no_bisect():
    versions = [f"v{i}" for i in range(5)]

    def eval_fn(v):
        return 0.0

    rep = bs.bisect_single_axis(versions, eval_fn, baseline_idx=0, current_idx=4, threshold=0.5)
    assert rep.found is False


def test_steps_recorded():
    versions = [f"v{i}" for i in range(8)]

    def eval_fn(v):
        idx = int(v[1:])
        return SCORES_REG_AT_5[idx]

    rep = bs.bisect_single_axis(versions, eval_fn, baseline_idx=0, current_idx=7, threshold=0.5)
    decisions = [s.decision for s in rep.steps]
    assert "found" in decisions
    assert decisions[-1] == "found"


def test_call_count_logarithmic():
    versions = [f"v{i}" for i in range(8)]
    calls = []

    def eval_fn(v):
        idx = int(v[1:])
        calls.append(idx)
        return SCORES_REG_AT_5[idx]

    bs.bisect_single_axis(versions, eval_fn, baseline_idx=0, current_idx=7, threshold=0.5)
    # baseline + current + log2(7) probes + final score-fetch for 'found' step
    # tight bound: <= 8 unique evaluations is more than enough
    assert len(calls) <= 8


def test_objects_with_version_id_attribute():
    class V:
        def __init__(self, vid, score):
            self.version_id = vid
            self.score = score

    versions = [V(f"v{i}", SCORES_REG_AT_5[i]) for i in range(8)]

    def eval_fn(v):
        return v.score

    rep = bs.bisect_single_axis(versions, eval_fn, baseline_idx=0, current_idx=7, threshold=0.5)
    assert rep.version_id == "v5"


def test_axis_passed_to_report_and_steps():
    versions = [f"v{i}" for i in range(4)]

    def eval_fn(v):
        return 1.0 if int(v[1:]) < 2 else 0.0

    rep = bs.bisect_single_axis(
        versions, eval_fn, baseline_idx=0, current_idx=3, threshold=0.5, axis="model"
    )
    assert rep.axis == "model"
    for s in rep.steps:
        assert s.axis == "model"


def test_simple_two_version_regression():
    versions = ["v0", "v1"]

    def eval_fn(v):
        return 1.0 if v == "v0" else 0.0

    rep = bs.bisect_single_axis(versions, eval_fn, baseline_idx=0, current_idx=1, threshold=0.5)
    assert rep.found is True
    assert rep.version_id == "v1"
