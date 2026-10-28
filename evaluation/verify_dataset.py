"""Inspect the published archive without API calls or changes to research data.

Consistency is not scientific validity. Error-bearing records are reported,
not silently removed or reinterpreted as model refusals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

IDENTITY_FIELDS = ("model_admin", "payload_id", "condition", "repetition")
GROUPS = {
    "by_model": "model_admin",
    "by_category": "category",
    "by_condition": "condition",
}


class ArchiveValidationError(ValueError):
    """The archive is malformed or disagrees with its published counts."""


def load_records(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ArchiveValidationError(f"Invalid JSON at line {number}") from exc
            if not isinstance(record, dict):
                raise ArchiveValidationError(f"Expected an object at line {number}")
            records.append(record)
    if not records:
        raise ArchiveValidationError("The archive contains no records")
    return records


def has_error_marker(record: dict) -> bool:
    """A conservative text marker, not a complete provider-error classifier."""
    return any(
        "[ERROR:" in str(record.get(stage, {}).get(field, ""))
        for stage, field in (
            ("parser_stage", "parser_response"),
            ("admin_stage", "admin_response"),
        )
    )


def validate_records(records: list[dict], payloads: list[dict]) -> None:
    if not payloads or not all(isinstance(p, dict) for p in payloads):
        raise ArchiveValidationError("Benchmark must be a non-empty list of objects")
    payload_ids = [p.get("id") for p in payloads]
    if not all(isinstance(p, str) and p for p in payload_ids):
        raise ArchiveValidationError("Benchmark payload IDs must be non-empty strings")
    if len(set(payload_ids)) != len(payload_ids):
        raise ArchiveValidationError("Benchmark contains duplicate payload IDs")
    categories = {p["id"]: p.get("category") for p in payloads}
    identities = set()
    for number, record in enumerate(records, 1):
        for field in ("model_admin", "payload_id", "condition", "category"):
            if not isinstance(record.get(field), str) or not record[field]:
                raise ArchiveValidationError(f"Invalid {field} in record {number}")
        if type(record.get("repetition")) is not int or record["repetition"] not in (
            1,
            2,
            3,
        ):
            raise ArchiveValidationError(f"Invalid repetition in record {number}")
        outcome = record.get("outcome")
        if (
            not isinstance(outcome, dict)
            or type(outcome.get("tool_executed")) is not bool
        ):
            raise ArchiveValidationError(f"Missing boolean outcome in record {number}")
        for stage in ("parser_stage", "admin_stage"):
            if not isinstance(record.get(stage), dict):
                raise ArchiveValidationError(f"Invalid {stage} in record {number}")
        if record["payload_id"] not in categories:
            raise ArchiveValidationError(f"Unknown payload in record {number}")
        if categories[record["payload_id"]] != record["category"]:
            raise ArchiveValidationError(
                f"Payload/category mismatch in record {number}"
            )
        identity = tuple(record[field] for field in IDENTITY_FIELDS)
        if identity in identities:
            raise ArchiveValidationError(
                f"Duplicate experiment identity in record {number}"
            )
        identities.add(identity)


def summarize(records: list[dict]) -> dict:
    groups = defaultdict(Counter)
    for record in records:
        group = groups[record["model_admin"]]
        error = has_error_marker(record)
        executed = record["outcome"]["tool_executed"]
        group["records"] += 1
        group["recorded_tool_executions"] += executed
        group["records_with_error_markers"] += error
        group["tool_executions_with_error_markers"] += error and executed
    keys = (
        "records",
        "recorded_tool_executions",
        "records_with_error_markers",
        "tool_executions_with_error_markers",
    )
    return {
        **{key: sum(group[key] for group in groups.values()) for key in keys},
        "unique_payload_ids": len({record["payload_id"] for record in records}),
        "model_labels": len(groups),
        "by_model": {model: dict(groups[model]) for model in sorted(groups)},
    }


def compare_published_counts(records: list[dict], published: dict) -> None:
    def compare(actual: dict, expected: dict, label: str) -> None:
        for field in ("n", "k"):
            if type(expected.get(field)) is not int or actual[field] != expected[field]:
                raise ArchiveValidationError(
                    f"Published {label}.{field} does not match archive"
                )
        expected_asr = expected.get("asr")
        actual_asr = 100 * actual["k"] / actual["n"]
        if (
            not isinstance(expected_asr, (int, float))
            or abs(actual_asr - expected_asr) > 1e-8
        ):
            raise ArchiveValidationError(
                f"Published {label}.asr does not match archive"
            )

    compare(
        {"n": len(records), "k": sum(r["outcome"]["tool_executed"] for r in records)},
        published.get("overall", {}),
        "overall",
    )
    for section, field in GROUPS.items():
        actual = defaultdict(lambda: {"n": 0, "k": 0})
        for record in records:
            actual[record[field]]["n"] += 1
            actual[record[field]]["k"] += record["outcome"]["tool_executed"]
        expected = published.get(section, {})
        if set(actual) != set(expected):
            raise ArchiveValidationError(
                f"Published {section} groups do not match archive"
            )
        for key, counts in actual.items():
            compare(counts, expected[key], f"{section}.{key}")


def audit_archive(root: Path) -> dict:
    paths = {
        "log": root / "sandbox/logs/attacks.jsonl",
        "benchmark": root / "benchmark/benchmark_v3_escalated.json",
        "published_statistics": root / "results/final_stats_v3.json",
    }
    records = load_records(paths["log"])
    payloads = json.loads(paths["benchmark"].read_text(encoding="utf-8"))
    if not isinstance(payloads, list):
        raise ArchiveValidationError("Benchmark must be a list")
    validate_records(records, payloads)
    published = json.loads(paths["published_statistics"].read_text(encoding="utf-8"))
    compare_published_counts(records, published)
    return {
        "archive_consistent": True,
        "interpretation": "Historical counts only; not a validated model or defense ranking.",
        "sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in paths.items()
        },
        **summarize(records),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Also fail if either agent response contains an [ERROR: marker",
    )
    args = parser.parse_args(argv)
    try:
        report = audit_archive(args.root)
    except (ArchiveValidationError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Archive verification failed: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_clean and report["records_with_error_markers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
