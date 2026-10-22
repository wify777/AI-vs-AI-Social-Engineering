"""Tests for diagnose_stop.py.

Run: python3 -m unittest discover -s team_work/timofey -p 'test_*.py' -v
"""

import copy
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from diagnose_stop import diagnose, main

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    with open(FIXTURES / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def variant(name, **changes):
    """A fixture with some fields changed."""
    snapshot = load(name)
    snapshot.update(changes)
    return snapshot


class DiagnoseTestCase(unittest.TestCase):
    def assertAction(self, snapshot, expected):
        result = diagnose(snapshot)
        self.assertEqual(result["action"], expected, result["reason"])
        return result


class FixtureTests(DiagnoseTestCase):
    def test_retry_candidate(self):
        result = self.assertAction(load("retry_candidate"), "retry_candidate")
        self.assertTrue(any("logs" in check for check in result["checks_needed"]))

    def test_running(self):
        self.assertAction(load("running"), "running")

    def test_wait_quota(self):
        self.assertAction(load("wait_quota"), "wait_quota")

    def test_review(self):
        self.assertAction(load("review"), "review_required")

    def test_integrity(self):
        self.assertAction(load("integrity"), "manual_check")

    def test_finished(self):
        self.assertAction(load("finished"), "finished")

    def test_stop_limit(self):
        self.assertAction(load("stop_limit"), "stop_limit")

    def test_result_shape(self):
        for path in sorted(FIXTURES.glob("*.json")):
            with self.subTest(fixture=path.name):
                result = diagnose(load(path.stem))
                self.assertEqual(set(result), {"action", "reason", "checks_needed"})
                self.assertIsInstance(result["reason"], str)
                self.assertIsInstance(result["checks_needed"], list)


class CombinationTests(DiagnoseTestCase):
    def test_process_alive_beats_deadline_expired(self):
        snapshot = variant("running", deadline_expired=True)
        self.assertAction(snapshot, "running")

    def test_hash_mismatch_beats_429(self):
        snapshot = variant("wait_quota", hashes_match=False)
        result = self.assertAction(snapshot, "manual_check")
        self.assertIn("hashes do not match", result["reason"])

    def test_integrity_beats_live_process(self):
        snapshot = variant("running", hashes_match=False)
        self.assertAction(snapshot, "manual_check")

    def test_running_count_with_dead_process(self):
        snapshot = variant("retry_candidate", running=1, failed=0)
        result = self.assertAction(snapshot, "manual_check")
        self.assertIn("running=1", result["reason"])

    def test_missing_process_alive(self):
        snapshot = load("retry_candidate")
        del snapshot["process_alive"]
        result = self.assertAction(snapshot, "manual_check")
        self.assertIn("missing field: process_alive", result["reason"])

    def test_counts_do_not_add_up(self):
        snapshot = variant("retry_candidate", planned=3)
        result = self.assertAction(snapshot, "manual_check")
        self.assertIn("counts do not add up", result["reason"])

    def test_network_error_with_stub_recorded(self):
        snapshot = variant("retry_candidate", stub_recorded=True)
        result = self.assertAction(snapshot, "manual_check")
        self.assertIn("stub_recorded is true", result["reason"])

    def test_http_headroom_8_below_required_9(self):
        snapshot = variant("retry_candidate", http_reservations_remaining=8)
        self.assertAction(snapshot, "stop_limit")

    def test_http_headroom_9_equal_to_required_9(self):
        snapshot = variant("retry_candidate", http_reservations_remaining=9)
        self.assertAction(snapshot, "retry_candidate")

    def test_wrong_types(self):
        cases = {
            "string instead of bool": {"process_alive": "false"},
            "zero instead of bool": {"lock_busy": 0},
            "bool instead of count": {"failed": True},
            "string instead of count": {"planned": "1"},
            "float instead of count": {"failed": 1.0},
            "null instead of bool": {"hashes_match": None},
            "bool inside http_statuses": {"http_statuses": [False, None, None]},
        }
        for label, changes in cases.items():
            with self.subTest(label):
                self.assertAction(variant("retry_candidate", **changes), "manual_check")

    def test_negative_count(self):
        snapshot = variant("retry_candidate", failed=-1, completed=2)
        self.assertAction(snapshot, "manual_check")

    def test_not_a_json_object(self):
        for value in ([], "text", None, 5):
            with self.subTest(value=value):
                self.assertAction(value, "manual_check")

    def test_finished_beats_deadline_expired(self):
        snapshot = variant("finished", deadline_expired=True)
        self.assertAction(snapshot, "finished")

    def test_review_only_is_finished_and_reported(self):
        snapshot = variant("finished", completed=0, review=1)
        result = self.assertAction(snapshot, "finished")
        self.assertTrue(any("review" in check for check in result["checks_needed"]))

    def test_provider_hold_waits(self):
        snapshot = variant("retry_candidate", provider_hold=True)
        self.assertAction(snapshot, "wait_quota")

    def test_no_attempts_left_is_stop_limit(self):
        snapshot = variant("retry_candidate", job_attempts_remaining=0)
        self.assertAction(snapshot, "stop_limit")

    def test_non_network_error_is_manual_check(self):
        snapshot = variant("retry_candidate", last_error="api_error_bad_request")
        self.assertAction(snapshot, "manual_check")

    def test_previous_attempts_not_preserved_is_manual_check(self):
        snapshot = variant("retry_candidate", previous_attempts_preserved=False)
        self.assertAction(snapshot, "manual_check")

    def test_input_not_mutated(self):
        for path in sorted(FIXTURES.glob("*.json")):
            with self.subTest(fixture=path.name):
                snapshot = load(path.stem)
                before = copy.deepcopy(snapshot)
                diagnose(snapshot)
                self.assertEqual(snapshot, before)


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["diagnose_stop.py", *args])
        return code, out.getvalue(), err.getvalue()

    def test_cli_prints_json_result(self):
        code, output, _ = self.run_cli(str(FIXTURES / "retry_candidate.json"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["action"], "retry_candidate")

    def test_cli_without_argument_fails(self):
        code, _, error = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("usage", error)

    def test_cli_missing_file_fails(self):
        code, _, error = self.run_cli(str(FIXTURES / "does_not_exist.json"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", error)


if __name__ == "__main__":
    unittest.main()
