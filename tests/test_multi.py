import sornaris.multi as bm


class FakeReport:
    def __init__(self, found, axis, version_id):
        self.found = found
        self.axis = axis
        self.version_id = version_id
        self.baseline_score = 1.0
        self.regressed_score = 0.0
        self.steps = []
        self.examples_failed = None


def test_priority_order_default_is_sorted(monkeypatch):
    seen = []

    def fake_single(versions, eval_fn, b, c, threshold, axis="prompt"):
        seen.append(axis)
        return FakeReport(found=False, axis=axis, version_id=None)

    monkeypatch.setattr(bm, "bisect_single_axis", fake_single)
    axes = {
        "zzz": {"versions": ["a", "b"], "baseline_idx": 0, "current_idx": 1},
        "aaa": {"versions": ["a", "b"], "baseline_idx": 0, "current_idx": 1},
        "mmm": {"versions": ["a", "b"], "baseline_idx": 0, "current_idx": 1},
    }
    bm.bisect_multi_axis(axes, lambda probe: 1.0, threshold=0.5)
    assert seen == ["aaa", "mmm", "zzz"]


def test_priority_explicit_order(monkeypatch):
    seen = []

    def fake_single(versions, eval_fn, b, c, threshold, axis="prompt"):
        seen.append(axis)
        return FakeReport(found=False, axis=axis, version_id=None)

    monkeypatch.setattr(bm, "bisect_single_axis", fake_single)
    axes = {
        "prompt": {"versions": ["p0", "p1"], "baseline_idx": 0, "current_idx": 1},
        "model": {"versions": ["m0", "m1"], "baseline_idx": 0, "current_idx": 1},
    }
    bm.bisect_multi_axis(axes, lambda probe: 1.0, threshold=0.5, priority=["model", "prompt"])
    assert seen == ["model", "prompt"]


def test_returns_report_per_axis(monkeypatch):
    def fake_single(versions, eval_fn, b, c, threshold, axis="prompt"):
        return FakeReport(found=True, axis=axis, version_id="guilty")

    monkeypatch.setattr(bm, "bisect_single_axis", fake_single)
    axes = {
        "prompt": {"versions": ["p0", "p1"], "baseline_idx": 0, "current_idx": 1},
        "model": {"versions": ["m0", "m1"], "baseline_idx": 0, "current_idx": 1},
    }
    reports = bm.bisect_multi_axis(axes, lambda probe: 0.0, threshold=0.5)
    assert set(reports.keys()) == {"prompt", "model"}
    assert reports["prompt"].found is True
    assert reports["model"].found is True


def test_evaluate_fn_receives_full_probe(monkeypatch):
    captured = []

    def fake_single(versions, eval_fn, b, c, threshold, axis="prompt"):
        eval_fn(versions[0])
        return FakeReport(found=False, axis=axis, version_id=None)

    monkeypatch.setattr(bm, "bisect_single_axis", fake_single)
    axes = {
        "prompt": {"versions": ["p0", "p1", "p2"], "baseline_idx": 0, "current_idx": 2},
        "model": {"versions": ["m0", "m1", "m2"], "baseline_idx": 0, "current_idx": 2},
    }

    def evf(probe):
        captured.append(dict(probe))
        return 1.0

    bm.bisect_multi_axis(axes, evf, threshold=0.5)
    assert len(captured) == 2
    for probe in captured:
        assert set(probe.keys()) == {"prompt", "model"}


def test_pinned_starts_at_current(monkeypatch):
    captured = []

    def fake_single(versions, eval_fn, b, c, threshold, axis="prompt"):
        eval_fn(versions[0])
        return FakeReport(found=False, axis=axis, version_id=None)

    monkeypatch.setattr(bm, "bisect_single_axis", fake_single)
    axes = {
        "prompt": {"versions": ["p0", "p1", "p2"], "baseline_idx": 0, "current_idx": 2},
        "model": {"versions": ["m0", "m1", "m2"], "baseline_idx": 0, "current_idx": 2},
    }

    def evf(probe):
        captured.append(dict(probe))
        return 1.0

    bm.bisect_multi_axis(axes, evf, threshold=0.5, priority=["prompt", "model"])
    # First call: prompt is probed (at p0), model pinned at current (p2 / m2). Capture model value.
    assert captured[0]["model"] == "m2"
    # Second call: model is probed (at m0), prompt pinned at current (p2).
    assert captured[1]["prompt"] == "p2"


def test_empty_axes_returns_empty_dict():
    out = bm.bisect_multi_axis({}, lambda p: 1.0, threshold=0.5)
    assert out == {}
