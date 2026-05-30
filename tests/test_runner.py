import pytest
import sornaris.runner as br

# Use the inline stubs from the module itself for type matching
PV = br.PromptVersion
MV = br.ModelVersion
EX = br.EvalExample


class DictCache:
    def __init__(self):
        self.data = {}
        self.set_calls = 0

    def has(self, k):
        return k in self.data

    def get(self, k):
        return self.data.get(k)

    def set(self, k, v):
        self.data[k] = v
        self.set_calls += 1


class ConstProvider:
    def __init__(self, value, count_calls=False):
        self.value = value
        self.calls = 0

    def generate(self, prompt, model_id):
        self.calls += 1
        return self.value


class ExactScorer:
    def score(self, output, expected):
        return 1.0 if output == expected else 0.0


def test_run_eval_no_cache_calls_provider():
    pv = PV(version_id="v1", content="Be concise.")
    mv = MV(model_id="gpt-4")
    ex = [
        EX(example_id="e1", input="hello", expected="hi"),
        EX(example_id="e2", input="world", expected="hi"),
    ]
    prov = ConstProvider("hi")
    results, mean = br.run_eval(pv, mv, ex, prov, ExactScorer())
    assert prov.calls == 2
    assert mean == 1.0
    assert len(results) == 2


def test_run_eval_returns_eval_results():
    pv = PV(version_id="v1", content="X")
    mv = MV(model_id="m")
    ex = [EX(example_id="only", input="in", expected="out")]
    prov = ConstProvider("out")
    results, _ = br.run_eval(pv, mv, ex, prov, ExactScorer())
    assert results[0].example_id == "only"
    assert results[0].score == 1.0


def test_run_eval_mean_score():
    pv = PV(version_id="v", content="c")
    mv = MV(model_id="m")
    ex = [
        EX(example_id="e1", input="a", expected="X"),
        EX(example_id="e2", input="b", expected="X"),
        EX(example_id="e3", input="c", expected="not-X"),
    ]
    prov = ConstProvider("X")
    _, mean = br.run_eval(pv, mv, ex, prov, ExactScorer())
    assert mean == pytest.approx(2 / 3)


def test_run_eval_uses_cache_when_hit():
    cache = DictCache()
    cache.data["x"] = 0.0  # not the real key — we'll fake the key construction
    pv = PV(version_id="v", content="c")
    mv = MV(model_id="m")
    ex = [EX(example_id="e1", input="in", expected="out")]
    prov = ConstProvider("out")
    # First call populates cache for real key
    results1, _ = br.run_eval(pv, mv, ex, prov, ExactScorer(), cache=cache)
    assert prov.calls == 1
    # Second call should hit cache, not provider
    results2, _ = br.run_eval(pv, mv, ex, prov, ExactScorer(), cache=cache)
    assert prov.calls == 1
    assert results2[0].output == "__cached__"
    assert results2[0].score == results1[0].score


def test_run_eval_writes_to_cache_on_miss():
    cache = DictCache()
    pv = PV(version_id="v", content="c")
    mv = MV(model_id="m")
    ex = [EX(example_id="e1", input="in", expected="out")]
    prov = ConstProvider("out")
    br.run_eval(pv, mv, ex, prov, ExactScorer(), cache=cache)
    assert cache.set_calls == 1


def test_run_eval_template_includes_prompt_and_input():
    pv = PV(version_id="v", content="SYSTEM_PROMPT_TEXT")
    mv = MV(model_id="m")
    ex = [EX(example_id="e1", input="USER_INPUT_TEXT", expected="ok")]
    seen = []

    class CapturingProvider:
        def generate(self, prompt, model_id):
            seen.append(prompt)
            return "ok"

    br.run_eval(pv, mv, ex, CapturingProvider(), ExactScorer())
    assert "SYSTEM_PROMPT_TEXT" in seen[0]
    assert "USER_INPUT_TEXT" in seen[0]


def test_run_eval_empty_examples_returns_zero():
    pv = PV(version_id="v", content="c")
    mv = MV(model_id="m")
    results, mean = br.run_eval(pv, mv, [], ConstProvider("x"), ExactScorer())
    assert results == []
    assert mean == 0.0
