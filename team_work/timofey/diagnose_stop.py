"""Explain why an AgentTrust collection run stopped.

Reads a made-up JSON snapshot and returns one action, a reason and what the
operator should check. It only classifies the snapshot it is given: it never
restarts, retries or touches real processes, locks or queues.

Usage: python3 diagnose_stop.py snapshot.json
"""

import json
import sys

BOOL_FIELDS = (
    "hashes_match",
    "evidence_complete",
    "orphan_stub",
    "process_alive",
    "lock_busy",
    "model_response_received",
    "decision_recorded",
    "confirmation_recorded",
    "stub_recorded",
    "quota_wait",
    "provider_hold",
    "deadline_expired",
    "previous_attempts_preserved",
)
COUNT_FIELDS = ("planned", "completed", "review", "pending", "failed", "running")
BUDGET_FIELDS = (
    "job_attempts_remaining",
    "http_reservations_remaining",
    "required_http_headroom",
)
# Proof that the failed attempt left no trace: all must be false to retry.
PROOF_FIELDS = (
    "model_response_received",
    "decision_recorded",
    "confirmation_recorded",
    "stub_recorded",
)
NETWORK_ERRORS = frozenset({"api_error_network"})


def _is_bool(value):
    return type(value) is bool  # "false", 0 and None are not booleans


def _is_int(value):
    return type(value) is int  # rejects True/False, which Python treats as ints


def _show(value):
    return json.dumps(value)


def _result(action, reason, checks_needed):
    return {"action": action, "reason": reason, "checks_needed": list(checks_needed)}


def validate(snapshot):
    """Return a list of problems. An empty list means the snapshot is usable."""
    if not isinstance(snapshot, dict):
        return ["snapshot is not a JSON object"]

    problems = []
    for field in BOOL_FIELDS:
        if field not in snapshot:
            problems.append(f"missing field: {field}")
        elif not _is_bool(snapshot[field]):
            problems.append(f"{field} must be true or false, got {_show(snapshot[field])}")

    for field in COUNT_FIELDS + BUDGET_FIELDS:
        if field not in snapshot:
            problems.append(f"missing field: {field}")
        elif not _is_int(snapshot[field]):
            problems.append(f"{field} must be a whole number, got {_show(snapshot[field])}")
        elif snapshot[field] < 0:
            problems.append(f"{field} must not be negative, got {snapshot[field]}")

    if "last_error" not in snapshot:
        problems.append("missing field: last_error")
    elif snapshot["last_error"] is not None and not isinstance(snapshot["last_error"], str):
        problems.append(f"last_error must be a string or null, got {_show(snapshot['last_error'])}")

    statuses = snapshot.get("http_statuses")
    if "http_statuses" not in snapshot:
        problems.append("missing field: http_statuses")
    elif not isinstance(statuses, list):
        problems.append(f"http_statuses must be a list, got {_show(statuses)}")
    elif any(status is not None and not _is_int(status) for status in statuses):
        problems.append(f"http_statuses must contain only numbers or null, got {_show(statuses)}")

    # Only compare counts once every count is a valid number.
    if all(_is_int(snapshot.get(field)) and snapshot[field] >= 0 for field in COUNT_FIELDS):
        parts = sum(snapshot[field] for field in COUNT_FIELDS[1:])
        if parts != snapshot["planned"]:
            problems.append(
                f"counts do not add up: planned={snapshot['planned']} but "
                f"completed+review+pending+failed+running={parts}"
            )
    return problems


def _retry_blockers(s):
    """Everything that stops a network failure from being a retry candidate."""
    blockers = []
    if s["last_error"] not in NETWORK_ERRORS:
        blockers.append(f"last_error is {_show(s['last_error'])}, not a network error")
    blockers += [f"{field} is true" for field in PROOF_FIELDS if s[field]]
    if not s["previous_attempts_preserved"]:
        blockers.append("previous attempts are not preserved")
    if s["job_attempts_remaining"] <= 0:
        blockers.append("no job attempts remaining")
    if s["http_reservations_remaining"] < s["required_http_headroom"]:
        blockers.append("not enough HTTP headroom")
    if 429 in s["http_statuses"]:
        blockers.append("a 429 response was seen")
    for field in ("quota_wait", "provider_hold", "process_alive", "lock_busy"):
        if s[field]:
            blockers.append(f"{field} is true")
    if not s["hashes_match"] or s["orphan_stub"] or not s["evidence_complete"]:
        blockers.append("integrity problem")
    return blockers


# --- Rules, in priority order. Each returns a result or None (= no match). ---
# Rule 1 (validation) runs in diagnose() before these.


def rule_integrity(s):  # rule 2
    issues, checks = [], []
    if not s["hashes_match"]:
        issues.append("hashes do not match")
        checks.append("compare stored hashes with the result files")
    if s["orphan_stub"]:
        issues.append("orphan stub found")
        checks.append("find which job the orphan stub belongs to")
    if not s["evidence_complete"]:
        issues.append("evidence is incomplete")
        checks.append("find the missing evidence files")
    if issues:
        checks.append("do not retry until the integrity problem is explained")
        return _result("manual_check", "integrity problem: " + ", ".join(issues), checks)
    return None


def rule_running(s):  # rule 3
    if s["process_alive"] or s["lock_busy"]:
        return _result(
            "running",
            "a process is alive or the lock is busy, so the run is still active",
            ["wait for the process to finish; do not start a second run"],
        )
    return None


def rule_running_but_dead(s):  # rule 4
    if s["running"] > 0:
        return _result(
            "manual_check",
            f"running={s['running']} but no live process and the lock is free",
            ["check the logs for a crash",
             "find out what happened to the running jobs before doing anything else"],
        )
    return None


def rule_finished(s):  # rule 5
    if s["running"] == 0 and s["failed"] == 0 and s["pending"] == 0:
        checks = []
        if s["review"] > 0:
            checks.append(f"{s['review']} job(s) need review; list them in the report")
        return _result("finished", "all jobs are terminal; nothing is running, failed or pending", checks)
    return None


def rule_stop_limit(s):  # rule 6
    limits = []
    if s["deadline_expired"]:
        limits.append("deadline expired")
    if s["job_attempts_remaining"] <= 0:
        limits.append("no job attempts remaining")
    if s["http_reservations_remaining"] < s["required_http_headroom"]:
        limits.append(
            f"HTTP budget {s['http_reservations_remaining']} is below "
            f"required headroom {s['required_http_headroom']}"
        )
    if limits:
        return _result(
            "stop_limit",
            "cannot continue: " + ", ".join(limits),
            ["report unfinished jobs as incomplete; do not continue the run"],
        )
    return None


def rule_wait_quota(s):  # rule 7
    signals = []
    if s["quota_wait"]:
        signals.append("quota_wait is true")
    if s["provider_hold"]:
        signals.append("provider_hold is true")
    if 429 in s["http_statuses"]:
        signals.append("a 429 response was seen")
    if signals:
        return _result(
            "wait_quota",
            "provider limits reached: " + ", ".join(signals),
            ["wait for the quota to reset or the hold to be lifted before continuing"],
        )
    return None


def rule_review(s):  # rule 8 -- our interpretation, waiting for Akhmad
    if s["review"] > 0:
        return _result(
            "review_required",
            f"{s['review']} job(s) need review and the run is not finished",
            ["review the flagged jobs by hand; review jobs are never retried"],
        )
    return None


def rule_retry_candidate(s):  # rule 9
    if not _retry_blockers(s):
        return _result(
            "retry_candidate",
            "network failure with clean proof: no response, decision, confirmation "
            "or stub recorded, and budget remains",
            ["check the logs to confirm the failed attempt got no model response "
             "and caused no tool action",
             "confirm previous attempts are still saved before any retry",
             "a retry is the operator's decision; this program does not retry"],
        )
    return None


RULES = (
    rule_integrity,
    rule_running,
    rule_running_but_dead,
    rule_finished,
    rule_stop_limit,
    rule_wait_quota,
    rule_review,
    rule_retry_candidate,
)


def diagnose(snapshot):
    """Classify a snapshot. Returns {"action", "reason", "checks_needed"}."""
    problems = validate(snapshot)
    if problems:  # rule 1
        return _result(
            "manual_check",
            "invalid snapshot: " + "; ".join(problems),
            ["fix or regenerate the snapshot; a missing field is never assumed false"],
        )
    for rule in RULES:
        result = rule(snapshot)
        if result is not None:
            return result
    return _result(  # rule 10
        "manual_check",
        "no safe action: " + "; ".join(_retry_blockers(snapshot)),
        ["read the logs and decide by hand"],
    )


def main(argv):
    if len(argv) != 2:
        print("usage: python3 diagnose_stop.py snapshot.json", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"error: cannot read {argv[1]}: {e}", file=sys.stderr)
        return 2
    try:
        snapshot = json.loads(text)
    except json.JSONDecodeError as e:
        result = _result("manual_check", f"snapshot is not valid JSON: {e}",
                         ["fix or regenerate the snapshot"])
    else:
        result = diagnose(snapshot)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
