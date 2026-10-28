"""Small deterministic fixtures for statistics and checkpoint storage."""

import json

import pytest

from evaluation.analysis_pipeline import AnalysisPipeline
from evaluation.experiment_queue import ExperimentJob, ExperimentQueue, RateLimiter


def test_asr_is_computed_from_recorded_boolean_outcomes(tmp_path):
    path = tmp_path / "runs.jsonl"
    rows = [
        {"model_admin": "a", "category": "one", "outcome": {"tool_executed": value}}
        for value in (True, False, False, False)
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows))
    pipeline = AnalysisPipeline(str(path))
    assert pipeline.compute_asr_by_model()["a"]["asr_pct"] == 25
    assert pipeline.compute_asr_by_category()["one"]["total"] == 4


@pytest.mark.parametrize("successes,total", [(0, 20), (20, 20), (5, 20)])
def test_wilson_interval_stays_in_probability_bounds(tmp_path, successes, total):
    pipeline = AnalysisPipeline(str(tmp_path / "missing.jsonl"))
    lower, upper = pipeline.wilson_ci(successes, total)
    assert 0 <= lower <= 100 * successes / total <= upper <= 100


def test_zero_events_do_not_claim_a_measured_rate(tmp_path):
    pipeline = AnalysisPipeline(str(tmp_path / "missing.jsonl"))
    assert pipeline.generate_report()["total_runs"] == 0
    assert pipeline.compute_asr_by_model() == {}


def test_checkpoint_round_trip(tmp_path):
    kwargs = dict(
        queue_file=str(tmp_path / "queue.jsonl"),
        checkpoint_file=str(tmp_path / "checkpoint.json"),
    )
    queue = ExperimentQueue(**kwargs)
    queue.save_checkpoint(3, 10)
    assert ExperimentQueue(**kwargs).load_checkpoint() == 3


def test_queue_records_completion_state(tmp_path):
    queue = ExperimentQueue(
        queue_file=str(tmp_path / "queue.jsonl"),
        checkpoint_file=str(tmp_path / "checkpoint.json"),
    )
    queue.add_job(ExperimentJob("job-1", "p1", "a", "a", "test", "baseline", 1))
    queue.mark_completed("job-1", {"outcome": {"tool_executed": False}})
    assert queue.stats()["completed"] == 1
    assert queue.stats()["progress_pct"] == 100


def test_daily_rate_limit_fails_without_sleeping():
    with pytest.raises(RuntimeError, match="RPD limit exceeded"):
        RateLimiter(rpd=0, min_delay_ms=0).wait_if_needed()
