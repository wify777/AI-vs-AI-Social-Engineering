"""Archive checks must not turn provider failures into evidence of resistance."""

import copy
import json
from pathlib import Path

import pytest

from evaluation.verify_dataset import (
    ArchiveValidationError,
    audit_archive,
    compare_published_counts,
    has_error_marker,
    load_records,
    main,
    summarize,
    validate_records,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def record():
    return {
        "model_admin": "model-a",
        "payload_id": "p1",
        "category": "Authority Spoofing",
        "condition": "baseline",
        "repetition": 1,
        "outcome": {"tool_executed": False},
        "parser_stage": {"parser_response": "forwarded content"},
        "admin_stage": {"admin_response": "refused"},
    }


@pytest.fixture
def payloads():
    return [{"id": "p1", "category": "Authority Spoofing"}]


def test_published_archive_is_consistent():
    report = audit_archive(ROOT)
    assert report["archive_consistent"] is True
    assert report["records"] == 2475
    assert report["unique_payload_ids"] == 60
    assert report["model_labels"] == 6
    assert report["recorded_tool_executions"] == 170
    assert report["records_with_error_markers"] == 1931
    assert report["tool_executions_with_error_markers"] == 25


@pytest.mark.parametrize(
    "field", ["model_admin", "payload_id", "category", "condition", "repetition"]
)
def test_missing_identity_fields_fail(record, payloads, field):
    record.pop(field)
    with pytest.raises(ArchiveValidationError):
        validate_records([record], payloads)


@pytest.mark.parametrize("value", [None, "false", 0, 1])
def test_outcome_requires_a_boolean(record, payloads, value):
    record["outcome"]["tool_executed"] = value
    with pytest.raises(ArchiveValidationError, match="boolean"):
        validate_records([record], payloads)


def test_duplicate_experiment_identity_fails(record, payloads):
    with pytest.raises(ArchiveValidationError, match="Duplicate experiment"):
        validate_records([record, copy.deepcopy(record)], payloads)


def test_unknown_payload_fails(record, payloads):
    record["payload_id"] = "unknown"
    with pytest.raises(ArchiveValidationError, match="Unknown payload"):
        validate_records([record], payloads)


def test_category_mismatch_fails(record, payloads):
    record["category"] = "Gaslighting"
    with pytest.raises(ArchiveValidationError, match="mismatch"):
        validate_records([record], payloads)


def test_duplicate_payload_ids_fail(record, payloads):
    with pytest.raises(ArchiveValidationError, match="duplicate payload"):
        validate_records([record], payloads + payloads)


@pytest.mark.parametrize(
    "stage,field",
    [("parser_stage", "parser_response"), ("admin_stage", "admin_response")],
)
def test_error_at_either_stage_is_visible(record, stage, field):
    record[stage][field] = "[ERROR: 429]"
    assert has_error_marker(record)
    report = summarize([record])
    assert report["records_with_error_markers"] == 1
    assert report["recorded_tool_executions"] == 0


def test_success_with_a_parser_error_is_not_hidden(record):
    record["parser_stage"]["parser_response"] = "[ERROR: timeout]"
    record["outcome"]["tool_executed"] = True
    assert summarize([record])["tool_executions_with_error_markers"] == 1


def test_invalid_json_reports_line_without_payload(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text('{"secret": "do-not-echo"\n')
    with pytest.raises(ArchiveValidationError, match="line 1") as error:
        load_records(path)
    assert "do-not-echo" not in str(error.value)


@pytest.mark.parametrize("text", ["", "\n", "[]\n"])
def test_empty_or_non_object_archive_fails(tmp_path, text):
    path = tmp_path / "log.jsonl"
    path.write_text(text)
    with pytest.raises(ArchiveValidationError):
        load_records(path)


def test_published_counts_cannot_drift():
    records = load_records(ROOT / "sandbox/logs/attacks.jsonl")
    published = json.loads((ROOT / "results/final_stats_v3.json").read_text())
    published["overall"]["k"] += 1
    with pytest.raises(ArchiveValidationError, match="overall.k"):
        compare_published_counts(records, published)


def test_strict_mode_rejects_error_bearing_snapshot(capsys):
    assert main(["--root", str(ROOT), "--require-clean"]) == 1
    assert json.loads(capsys.readouterr().out)["archive_consistent"] is True
