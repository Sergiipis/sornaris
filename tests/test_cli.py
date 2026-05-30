import json
import pytest
import sornaris.cli as cli


def test_load_prompts_jsonl(tmp_path):
    f = tmp_path / "prompts.jsonl"
    f.write_text(
        '{"version_id": "v1", "content": "Be concise.", "parent_id": null, "timestamp": 1.0}\n'
        '{"version_id": "v2", "content": "Be very concise.", "parent_id": "v1", "timestamp": 2.0}\n'
    )
    prompts = cli.load_prompts_jsonl(str(f))
    assert len(prompts) == 2
    assert prompts[0].version_id == "v1"
    assert prompts[1].parent_id == "v1"


def test_load_prompts_skips_blank_lines(tmp_path):
    f = tmp_path / "prompts.jsonl"
    f.write_text(
        '{"version_id": "v1", "content": "X"}\n\n   \n{"version_id": "v2", "content": "Y"}\n'
    )
    prompts = cli.load_prompts_jsonl(str(f))
    assert len(prompts) == 2


def test_load_evals_jsonl(tmp_path):
    f = tmp_path / "eval.jsonl"
    f.write_text(
        '{"example_id": "e1", "input": "2+2", "expected": "4"}\n'
        '{"example_id": "e2", "input": "3+3", "expected": "6", "metadata": {"hard": true}}\n'
    )
    evals = cli.load_evals_jsonl(str(f))
    assert len(evals) == 2
    assert evals[0].expected == "4"
    assert evals[1].metadata == {"hard": True}


def test_report_to_dict_basic():
    class S:
        step_index = 0
        axis = "prompt"
        low_idx = 0
        high_idx = 7
        probed_idx = 3
        probed_score = 1.0
        decision = "go_right"

    class R:
        found = True
        axis = "prompt"
        version_id = "v5"
        baseline_score = 1.0
        regressed_score = 0.0
        steps = [S()]
        examples_failed = None

    d = cli.report_to_dict(R())
    assert d["found"] is True
    assert d["version_id"] == "v5"
    assert d["baseline_score"] == 1.0
    assert len(d["steps"]) == 1
    assert d["steps"][0]["decision"] == "go_right"


def test_main_run_writes_report_file(tmp_path):
    prompts = tmp_path / "p.jsonl"
    prompts.write_text(
        '{"version_id":"v0","content":"good"}\n{"version_id":"v1","content":"also good"}\n'
    )
    evals = tmp_path / "e.jsonl"
    evals.write_text('{"example_id":"e1","input":"x","expected":"anything"}\n')
    report = tmp_path / "out.json"
    rc = cli.main(
        [
            "run",
            "--prompts",
            str(prompts),
            "--evals",
            str(evals),
            "--report",
            str(report),
            "--threshold",
            "0.5",
        ]
    )
    assert rc == 0
    assert report.exists()
    data = json.loads(report.read_text())
    assert "found" in data
    assert "baseline_score" in data


def test_main_returns_nonzero_on_missing_prompts(tmp_path):
    evals = tmp_path / "e.jsonl"
    evals.write_text('{"example_id":"e1","input":"x","expected":"y"}\n')
    rc = cli.main(
        [
            "run",
            "--prompts",
            str(tmp_path / "nonexistent.jsonl"),
            "--evals",
            str(evals),
        ]
    )
    assert rc != 0


def test_main_no_args_returns_nonzero():
    rc = cli.main([])
    assert rc != 0


def test_load_models_jsonl(tmp_path):
    f = tmp_path / "models.jsonl"
    f.write_text(
        '{"model_id": "m1"}\n{"model_id": "m2", "provider": "openai", "version": "2024-01"}\n'
    )
    models = cli.load_models_jsonl(str(f))
    assert len(models) == 2
    assert models[0].model_id == "m1"
    assert models[1].provider == "openai"


def test_main_multi_axis_report_shape(tmp_path):
    prompts = tmp_path / "p.jsonl"
    prompts.write_text('{"version_id":"v0","content":"a"}\n{"version_id":"v1","content":"b"}\n')
    models = tmp_path / "m.jsonl"
    models.write_text('{"model_id":"m0"}\n{"model_id":"m1"}\n')
    evals = tmp_path / "e.jsonl"
    evals.write_text('{"example_id":"e1","input":"x","expected":"y"}\n')
    report = tmp_path / "out.json"
    rc = cli.main(
        [
            "run",
            "--prompts",
            str(prompts),
            "--models",
            str(models),
            "--evals",
            str(evals),
            "--report",
            str(report),
        ]
    )
    assert rc == 0
    data = json.loads(report.read_text())
    assert set(data.keys()) == {"prompt", "model"}
    assert "found" in data["prompt"]
    assert "found" in data["model"]


def test_main_unknown_provider_rejected_by_argparse(tmp_path):
    prompts = tmp_path / "p.jsonl"
    prompts.write_text('{"version_id":"v0","content":"a"}\n{"version_id":"v1","content":"b"}\n')
    evals = tmp_path / "e.jsonl"
    evals.write_text('{"example_id":"e1","input":"x","expected":"y"}\n')
    with pytest.raises(SystemExit):
        cli.main(["run", "--prompts", str(prompts), "--evals", str(evals), "--provider", "bogus"])
