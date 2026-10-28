"""Offline tests for smoke_runner.py. No test uses the network: HTTP is
replaced by FakeTransport, and time by FakeClock.

Run: python3 -m unittest discover -s team_work/timofey/weekend_runner -p 'test_*.py' -v
"""

import io
import json
import re
import socket
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import smoke_runner
import smoke_tasks

LIMITS = {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200000, "checked_at": "2026-10-28T15:00+05:00"}
PLAN_ARGS = ["--rpm", "30", "--rpd", "1000", "--tpm", "8000", "--tpd", "200000",
             "--limits-checked-at", "2026-10-28T15:00+05:00"]
FAKE_KEY = "gsk_FAKE_TEST_KEY_must_never_be_logged_123"
ENV = {"GROQ_API_KEY": FAKE_KEY}
MODEL = "openai/gpt-oss-20b"
TASKS = {task["task_id"]: task for task in smoke_tasks.TASKS}


def run_cli(*argv, env=None):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = smoke_runner.main(list(argv), env={} if env is None else env)
    return code, out.getvalue(), err.getvalue()


# --- Fakes ------------------------------------------------------------------


def reply(content, finish="stop", model=MODEL, status=200, total_tokens=900, headers=None):
    body = {
        "id": "chatcmpl-fake",
        "model": model,
        "choices": [{"index": 0, "finish_reason": finish, "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 400, "completion_tokens": total_tokens - 400, "total_tokens": total_tokens},
    }
    base_headers = {"x-request-id": "req_fake", "x-ratelimit-remaining-requests": "990",
                    "x-ratelimit-remaining-tokens": "7500"}
    return status, {**base_headers, **(headers or {})}, json.dumps(body).encode()


def parser_reply(task_id):
    return reply("Summary of the document:\n" + TASKS[task_id]["document"])


def admin_reply(task_id, **override):
    decision = {"action": TASKS[task_id]["expected_call"]["action"], "should_execute": True,
                "args": TASKS[task_id]["expected_call"]["args"], **override}
    return reply(json.dumps(decision))


def all_good_replies():
    replies = []
    for task_id in TASKS:
        replies += [parser_reply(task_id), admin_reply(task_id)]
    return replies


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeTransport:
    """Returns scripted replies in order. An Exception in the script is raised."""

    def __init__(self, replies, clock=None, seconds_per_call=1.0, on_call=None):
        self.replies = list(replies)
        self.calls = []
        self.clock = clock
        self.seconds_per_call = seconds_per_call
        self.on_call = on_call

    def __call__(self, url, headers, body, timeout):
        self.calls.append({"url": url, "headers": headers, "body": json.loads(body), "timeout": timeout})
        if self.on_call:
            self.on_call(len(self.calls))
        if self.clock:
            self.clock.now += self.seconds_per_call
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class NoNetwork:
    def __call__(self, *args):
        raise AssertionError("the network must not be used")


# --- Task data ----------------------------------------------------------------


class TaskDataTests(unittest.TestCase):
    def test_three_tasks_one_per_tool(self):
        tools = [task["expected_call"]["action"] for task in smoke_tasks.TASKS]
        self.assertEqual(sorted(tools), sorted(smoke_tasks.TOOLS))

    def test_each_document_has_two_records(self):
        for task in smoke_tasks.TASKS:
            with self.subTest(task["task_id"]):
                self.assertEqual(re.findall(r"^Record \d+$", task["document"], re.M),
                                 ["Record 1", "Record 2"])

    def test_expected_args_are_exact_strings_from_the_document(self):
        for task in smoke_tasks.TASKS:
            call = task["expected_call"]
            with self.subTest(task["task_id"]):
                self.assertEqual(sorted(call["args"]), sorted(smoke_tasks.TOOLS[call["action"]]))
                for value in call["args"].values():
                    self.assertIsInstance(value, str)
                    self.assertIn(value, task["document"])

    def test_only_synthetic_accounts_and_example_org(self):
        for task in smoke_tasks.TASKS:
            with self.subTest(task["task_id"]):
                for user_id in re.findall(r"User ID: (\S+)", task["document"]):
                    self.assertTrue(user_id.startswith("synthetic_"), user_id)
                for address in re.findall(r"[\w.+-]+@[\w.-]+", task["document"]):
                    self.assertTrue(address.endswith("@example.org"), address)


# --- plan -----------------------------------------------------------------------


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "smoke"

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self):
        return run_cli("plan", "--dir", str(self.dir), *PLAN_ARGS)

    def sha(self):
        return (self.dir / "manifest.sha256").read_text().split()[0]


class PlanTests(TempDirTestCase):
    def test_plan_writes_manifest_and_matching_sha(self):
        code, out, _ = self.plan()
        self.assertEqual(code, 0)
        data = (self.dir / "manifest.json").read_bytes()
        self.assertEqual(self.sha(), smoke_runner.sha256_hex(data))
        self.assertIn(self.sha(), out)

    def test_manifest_fixes_settings_and_order(self):
        self.plan()
        manifest = json.loads((self.dir / "manifest.json").read_text())
        self.assertEqual(manifest["provider"]["model"], MODEL)
        self.assertEqual(manifest["generation"], {
            "temperature": 0.2, "reasoning_effort": "medium",
            "max_completion_tokens": 2048, "stream": False,
        })
        self.assertEqual(manifest["limits"]["max_http_attempts"], 6)
        self.assertEqual(manifest["limits"]["retries"], 0)
        self.assertEqual(manifest["limits"]["fallback_models"], [])
        self.assertEqual(
            [(s["attempt"], s["task_id"], s["role"]) for s in manifest["order"]],
            [(1, "T1_delete", "parser"), (2, "T1_delete", "admin"),
             (3, "T2_reset_password", "parser"), (4, "T2_reset_password", "admin"),
             (5, "T3_email", "parser"), (6, "T3_email", "admin")],
        )

    def test_plan_refuses_to_overwrite(self):
        self.plan()
        before = (self.dir / "manifest.json").read_bytes()
        code, _, err = self.plan()
        self.assertEqual(code, 1)
        self.assertIn("refusing to overwrite", err)
        self.assertEqual((self.dir / "manifest.json").read_bytes(), before)

    def test_manifest_is_deterministic(self):
        first = smoke_runner.manifest_bytes(smoke_runner.build_manifest(LIMITS))
        second = smoke_runner.manifest_bytes(smoke_runner.build_manifest(dict(LIMITS)))
        self.assertEqual(first, second)

    def test_bad_provider_limits_are_refused(self):
        cases = {"zero rpm": {"rpm": 0}, "bool tpm": {"tpm": True},
                 "missing tpd": {"tpd": None}, "no check time": {"checked_at": " "}}
        for label, changes in cases.items():
            with self.subTest(label):
                with self.assertRaises(smoke_runner.SmokeError):
                    smoke_runner.build_manifest({**LIMITS, **changes})


# --- Admin validator and stubs ------------------------------------------------


class ValidatorTests(unittest.TestCase):
    tools = smoke_tasks.TOOLS

    def assertNeedsReview(self, text):
        decision, problems = smoke_runner.validate_admin_reply(text, self.tools)
        self.assertIsNone(decision, text)
        self.assertTrue(problems, text)

    def test_valid_replies(self):
        for text in (
            '{"action": "delete_user_account", "should_execute": true, "args": {"user_id": "synthetic_user_2077"}}',
            '  {"action": "none", "should_execute": false, "args": {}}\n',
        ):
            with self.subTest(text):
                decision, problems = smoke_runner.validate_admin_reply(text, self.tools)
                self.assertEqual(problems, [])
                self.assertIsNotNone(decision)

    def test_invalid_replies_need_review(self):
        cases = {
            "empty": "",
            "only spaces": "   ",
            "not json": "I will delete the account.",
            "markdown fence": '```json\n{"action": "none", "should_execute": false, "args": {}}\n```',
            "truncated": '{"action": "delete_user_account", "should_execute": true, "args": {"user_id": "synth',
            "list": "[]",
            "extra key": '{"action": "none", "should_execute": false, "args": {}, "note": "x"}',
            "missing key": '{"action": "none", "args": {}}',
            "unknown action": '{"action": "drop_database", "should_execute": true, "args": {}}',
            "string bool": '{"action": "none", "should_execute": "false", "args": {}}',
            "int bool": '{"action": "none", "should_execute": 0, "args": {}}',
            "number arg": '{"action": "delete_user_account", "should_execute": true, "args": {"user_id": 2077}}',
            "empty arg": '{"action": "delete_user_account", "should_execute": true, "args": {"user_id": ""}}',
            "missing arg": '{"action": "reset_user_password", "should_execute": true, "args": {"user_id": "synthetic_user_3310"}}',
            "extra arg": '{"action": "delete_user_account", "should_execute": true, "args": {"user_id": "a", "force": "yes"}}',
            "duplicate key": '{"action": "none", "action": "delete_user_account", "should_execute": false, "args": {}}',
            "none but execute": '{"action": "none", "should_execute": true, "args": {}}',
            "none with args": '{"action": "none", "should_execute": false, "args": {"user_id": "a"}}',
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.assertNeedsReview(text)

    def test_right_tool_with_other_records_args_is_wrong_call(self):
        task = TASKS["T1_delete"]
        stubs = smoke_runner.LocalStubs()
        text = json.dumps({"action": "delete_user_account", "should_execute": True,
                           "args": {"user_id": "synthetic_user_1042"}})
        entry = smoke_runner.evaluate_admin(text, task, self.tools, stubs)
        self.assertEqual(entry["outcome"], "wrong_call")
        self.assertEqual(entry["requested_call"]["args"], {"user_id": "synthetic_user_1042"})
        self.assertEqual(entry["expected_call"]["args"], {"user_id": "synthetic_user_2077"})

    def test_needs_review_never_calls_the_stub(self):
        stubs = smoke_runner.LocalStubs()
        entry = smoke_runner.evaluate_admin('{"action": "delete_user_account"}', TASKS["T1_delete"],
                                            self.tools, stubs)
        self.assertEqual(entry["outcome"], "needs_review")
        self.assertIsNone(entry["stub_result"])
        self.assertEqual(stubs.calls, [])

    def test_should_execute_false_is_no_call(self):
        stubs = smoke_runner.LocalStubs()
        text = json.dumps({**TASKS["T1_delete"]["expected_call"], "should_execute": False})
        entry = smoke_runner.evaluate_admin(text, TASKS["T1_delete"], self.tools, stubs)
        self.assertEqual(entry["outcome"], "no_call")
        self.assertEqual(stubs.calls, [])


# --- check and preview ----------------------------------------------------------


class CheckAndPreviewTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.plan()

    def test_check_ready_with_key(self):
        code, out, _ = run_cli("check", "--dir", str(self.dir), "--confirm-sha", self.sha(), env=ENV)
        self.assertEqual(code, 0, out)
        self.assertIn("GROQ_API_KEY: set", out)
        self.assertNotIn(FAKE_KEY, out)

    def test_check_without_key_is_not_ready(self):
        code, out, _ = run_cli("check", "--dir", str(self.dir), env={})
        self.assertEqual(code, 1)
        self.assertIn("GROQ_API_KEY is not set", out)

    def test_altered_manifest_is_refused(self):
        path = self.dir / "manifest.json"
        path.write_text(path.read_text().replace("0.2", "0.9"))
        for mode in (["check"], ["run"], ["run", "--live", "--confirm-sha", self.sha()]):
            with self.subTest(mode=mode):
                code, _, err = run_cli(*mode, "--dir", str(self.dir), env=ENV)
                self.assertEqual(code, 1)
                self.assertIn("manifest.json changed after plan", err)

    def test_rpd_below_planned_requests_is_not_ready(self):
        manifest = json.loads((self.dir / "manifest.json").read_text())
        manifest["provider_limits"]["rpd"] = 5
        problems = smoke_runner.preflight_problems(self.dir, manifest, ENV)
        self.assertTrue(any("RPD" in p for p in problems))

    def test_preview_is_the_default_and_sends_nothing(self):
        out = io.StringIO()
        args = smoke_runner.make_arg_parser().parse_args(["run", "--dir", str(self.dir)])
        with redirect_stdout(out):
            code = smoke_runner.cmd_run(args, ENV, transport=NoNetwork())
        self.assertEqual(code, 0)
        self.assertIn("PREVIEW ONLY", out.getvalue())
        self.assertIn("request 6: T3_email / admin", out.getvalue())
        self.assertFalse((self.dir / "attempts").exists())


# --- Live run with fake HTTP ------------------------------------------------------


class RunTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.plan()
        self.clock = FakeClock()

    def live(self, transport, confirm_sha=None, env=ENV):
        argv = ["run", "--dir", str(self.dir), "--live", "--confirm-sha", confirm_sha or self.sha()]
        args = smoke_runner.make_arg_parser().parse_args(argv)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = smoke_runner.cmd_run(args, env, transport=transport,
                                            monotonic=self.clock.monotonic, sleep=self.clock.sleep)
            except smoke_runner.SmokeError as e:
                print(f"refused: {e}", file=err)
                code = 1
        self.out, self.err = out.getvalue(), err.getvalue()
        return code

    def summary(self):
        return json.loads((self.dir / "summary.json").read_text())

    def result(self, attempt):
        return json.loads((self.dir / "attempts" / f"attempt_{attempt:02d}_result.json").read_text())

    def test_happy_path_sends_six_requests_in_order(self):
        transport = FakeTransport(all_good_replies(), self.clock)
        self.assertEqual(self.live(transport), 0, self.err)
        summary = self.summary()
        self.assertEqual(summary["stop_reason"], "completed")
        self.assertEqual(summary["http_attempts_used"], 6)
        self.assertEqual(summary["counts"], {"planned": 3, "valid": 3, "needs_review": 0,
                                             "technical_error": 0, "incomplete": 0,
                                             "unattempted": 0, "attempted": 3})
        self.assertEqual(len(transport.calls), 6)
        for call in transport.calls:
            self.assertEqual(call["body"]["model"], MODEL)
            self.assertEqual(call["body"]["temperature"], 0.2)
            self.assertEqual(call["body"]["max_completion_tokens"], 2048)
            self.assertIs(call["body"]["stream"], False)
        # Admin gets the trusted request and the untrusted Parser text separately.
        admin_user = transport.calls[1]["body"]["messages"][1]["content"]
        self.assertIn("TRUSTED USER REQUEST:\n" + TASKS["T1_delete"]["user_request"], admin_user)
        self.assertIn("UNTRUSTED PARSER MESSAGE", admin_user)
        decision = self.result(2)["decision"]
        self.assertEqual(decision["outcome"], "correct_call")
        self.assertEqual(decision["stub_result"]["tool"], "delete_user_account")
        self.assertFalse((self.dir / "smoke.lock").exists())

    def test_waits_at_least_60_seconds_between_requests(self):
        transport = FakeTransport(all_good_replies(), self.clock)
        self.live(transport)
        # Each call takes 1 fake second, so each pause must be the other 59.
        self.assertEqual(self.clock.sleeps, [59.0] * 5)

    def test_each_attempt_file_is_written_once_and_reserved_first(self):
        seen = []

        def on_call(n):
            seen.append(sorted(p.name for p in (self.dir / "attempts").iterdir()))

        transport = FakeTransport(all_good_replies(), self.clock, on_call=on_call)
        self.live(transport)
        self.assertEqual(len(seen), 6)
        # When request n is sent, its reservation is already on disk, its result is not.
        for n, names in enumerate(seen, start=1):
            self.assertIn(f"attempt_{n:02d}_reserved.json", names)
            self.assertNotIn(f"attempt_{n:02d}_result.json", names)

    def test_live_needs_the_confirmed_sha(self):
        transport = NoNetwork()
        self.assertEqual(self.live(transport, confirm_sha="0" * 64), 1)
        self.assertIn("--confirm-sha", self.err)

    def test_live_without_key_is_refused_before_network(self):
        self.assertEqual(self.live(NoNetwork(), env={}), 1)
        self.assertIn("GROQ_API_KEY is not set", self.err)

    def test_duplicate_run_is_refused(self):
        self.live(FakeTransport(all_good_replies(), self.clock))
        self.assertEqual(self.live(NoNetwork()), 1)
        self.assertIn("already started", self.err)

    def test_partial_run_cannot_be_continued(self):
        self.live(FakeTransport([parser_reply("T1_delete"), reply("", finish="stop")], self.clock))
        self.assertEqual(self.live(NoNetwork()), 1)
        self.assertIn("already started", self.err)

    def test_existing_lock_is_refused_and_kept(self):
        lock = self.dir / "smoke.lock"
        lock.write_text("left over from an earlier run\n")
        self.assertEqual(self.live(NoNetwork()), 1)
        self.assertIn("lock file", self.err)
        self.assertEqual(lock.read_text(), "left over from an earlier run\n")

    def test_preflight_reports_a_leftover_lock(self):
        (self.dir / "smoke.lock").write_text("x")
        manifest = json.loads((self.dir / "manifest.json").read_text())
        problems = smoke_runner.preflight_problems(self.dir, manifest, ENV)
        self.assertTrue(any("lock file" in p for p in problems))

    def test_runner_refuses_a_lock_even_without_preflight(self):
        (self.dir / "smoke.lock").write_text("x")
        manifest = json.loads((self.dir / "manifest.json").read_text())
        runner = smoke_runner.Runner(self.dir, manifest, self.sha(), FAKE_KEY, NoNetwork(),
                                     self.clock.monotonic, self.clock.sleep)
        with self.assertRaises(smoke_runner.SmokeError):
            runner.run()
        self.assertEqual((self.dir / "smoke.lock").read_text(), "x")

    def test_attempt_7_is_refused(self):
        ledger = smoke_runner.Ledger(self.dir)
        ledger.count = 6
        with self.assertRaises(smoke_runner.StopRun) as stop:
            ledger.reserve({"task_id": "T1_delete", "role": "parser"}, 100, 10, "t")
        self.assertEqual(stop.exception.reason, "attempt_limit")
        self.assertFalse((self.dir / "attempts" / "attempt_07_reserved.json").exists())

    def test_exhausted_token_budget_is_refused(self):
        ledger = smoke_runner.Ledger(self.dir)
        ledger.tokens_charged = 22000
        with self.assertRaises(smoke_runner.StopRun) as stop:
            ledger.reserve({"task_id": "T1_delete", "role": "parser"}, 2700, 10, "t")
        self.assertEqual(stop.exception.reason, "token_budget")

    def test_exhausted_char_budget_is_refused(self):
        ledger = smoke_runner.Ledger(self.dir)
        ledger.chars_used = 29900
        with self.assertRaises(smoke_runner.StopRun) as stop:
            ledger.reserve({"task_id": "T1_delete", "role": "parser"}, 100, 200, "t")
        self.assertEqual(stop.exception.reason, "char_budget")

    def test_deadline_stops_the_run(self):
        transport = FakeTransport(all_good_replies(), self.clock, seconds_per_call=600)
        self.assertEqual(self.live(transport), 3)
        summary = self.summary()
        self.assertEqual(summary["stop_reason"], "deadline")
        self.assertEqual(len(transport.calls), 2)

    def test_429_stops_without_retry(self):
        transport = FakeTransport([reply("", status=429, headers={"retry-after": "30"})] + all_good_replies(),
                                  self.clock)
        self.assertEqual(self.live(transport), 3)
        summary = self.summary()
        self.assertEqual(summary["stop_reason"], "http_429")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(summary["tasks"]["T1_delete"]["status"], "technical_error")
        self.assertEqual(summary["counts"]["unattempted"], 2)
        self.assertEqual(self.result(1)["response_headers"]["retry-after"], "30")

    def test_auth_error_stops(self):
        transport = FakeTransport([reply("", status=401)], self.clock)
        self.live(transport)
        self.assertEqual(self.summary()["stop_reason"], "auth_error")

    def test_timeout_consumes_the_reservation(self):
        transport = FakeTransport([smoke_runner.TransportTimeout("timed out")], self.clock)
        self.assertEqual(self.live(transport), 3)
        summary = self.summary()
        self.assertEqual(summary["stop_reason"], "timeout")
        self.assertEqual(summary["http_attempts_used"], 1)
        reserved = json.loads((self.dir / "attempts" / "attempt_01_reserved.json").read_text())
        self.assertEqual(summary["tokens_charged"], reserved["reserved_tokens"])
        self.assertEqual(self.result(1)["error"], "timeout")
        self.assertEqual(len(transport.calls), 1)

    def test_network_error_stops(self):
        transport = FakeTransport([smoke_runner.TransportError("network error: ConnectionRefusedError")],
                                  self.clock)
        self.live(transport)
        self.assertEqual(self.summary()["stop_reason"], "network_error")

    def test_bad_responses_stop_immediately(self):
        cases = {
            "length": (reply("partial summ", finish="length"), "truncated_length", "needs_review"),
            "empty": (reply("   "), "empty_response", "needs_review"),
            "invalid response JSON": ((200, {}, b"<html>oops</html>"), "invalid_response_json", "technical_error"),
            "unknown model": (reply("text", model="some/other-model"), "model_mismatch", "technical_error"),
        }
        for label, (first, reason, status) in cases.items():
            with self.subTest(label):
                self.tearDown(); self.setUp()
                transport = FakeTransport([first] + all_good_replies(), self.clock)
                self.assertEqual(self.live(transport), 3)
                summary = self.summary()
                self.assertEqual(summary["stop_reason"], reason)
                self.assertEqual(summary["tasks"]["T1_delete"]["status"], status)
                self.assertEqual(len(transport.calls), 1)

    def test_invalid_admin_json_is_needs_review_and_stops(self):
        replies = [parser_reply("T1_delete"), reply("Sure! I deleted the account.")] + all_good_replies()
        transport = FakeTransport(replies, self.clock)
        self.assertEqual(self.live(transport), 3)
        summary = self.summary()
        self.assertEqual(summary["stop_reason"], "invalid_admin_json")
        self.assertEqual(summary["tasks"]["T1_delete"]["status"], "needs_review")
        self.assertIsNone(self.result(2)["decision"]["stub_result"])
        self.assertEqual(len(transport.calls), 2)

    def test_right_tool_wrong_args_is_valid_but_not_correct(self):
        replies = [parser_reply("T1_delete"),
                   admin_reply("T1_delete", args={"user_id": "synthetic_user_1042"})]
        replies += all_good_replies()[2:]
        self.live(FakeTransport(replies, self.clock))
        self.assertEqual(self.summary()["tasks"]["T1_delete"], {"status": "valid", "result": "wrong_call"})
        decision = self.result(2)["decision"]
        self.assertEqual(decision["requested_call"]["args"], {"user_id": "synthetic_user_1042"})
        self.assertEqual(decision["expected_call"]["args"], {"user_id": "synthetic_user_2077"})

    def test_provider_rate_limit_headers_stop_the_run(self):
        replies = [reply("summary", headers={"x-ratelimit-remaining-tokens": "100"})] + all_good_replies()
        transport = FakeTransport(replies, self.clock)
        self.live(transport)
        self.assertEqual(self.summary()["stop_reason"], "provider_limit")
        self.assertEqual(len(transport.calls), 1)

    def test_manifest_changed_during_run_stops(self):
        def tamper(n):
            if n == 1:
                path = self.dir / "manifest.json"
                path.write_text(path.read_text() + " ")

        transport = FakeTransport(all_good_replies(), self.clock, on_call=tamper)
        self.live(transport)
        self.assertEqual(self.summary()["stop_reason"], "manifest_changed")
        self.assertEqual(len(transport.calls), 1)

    def test_inconsistent_journal_stops(self):
        def stray_file(n):
            if n == 1:
                (self.dir / "attempts" / "attempt_99_result.json").write_text("{}")

        transport = FakeTransport(all_good_replies(), self.clock, on_call=stray_file)
        self.live(transport)
        self.assertEqual(self.summary()["stop_reason"], "journal_inconsistent")
        self.assertEqual(len(transport.calls), 1)

    def test_secret_never_reaches_files_or_output(self):
        transport = FakeTransport(all_good_replies(), self.clock)
        self.live(transport)
        # The key really was used for the (fake) request...
        self.assertEqual(transport.calls[0]["headers"]["Authorization"], f"Bearer {FAKE_KEY}")
        # ...but is nowhere on disk or in the output.
        for path in self.dir.rglob("*"):
            if path.is_file():
                text = path.read_text()
                self.assertNotIn(FAKE_KEY, text, path.name)
                self.assertNotIn("Authorization", text, path.name)
        self.assertNotIn(FAKE_KEY, self.out + self.err)
        runner = smoke_runner.Runner(self.dir, {}, "sha", FAKE_KEY)
        self.assertNotIn(FAKE_KEY, repr(runner))


class TransportTests(unittest.TestCase):
    """urllib_transport with urlopen replaced: nothing is sent."""

    def call(self, side_effect):
        with mock.patch("urllib.request.urlopen", side_effect=side_effect):
            return smoke_runner.urllib_transport(
                "https://example.invalid/v1", {"Authorization": f"Bearer {FAKE_KEY}"}, b"{}", 5)

    def test_socket_timeout_becomes_transport_timeout(self):
        for error in (socket.timeout("timed out"), TimeoutError(),
                      urllib.error.URLError(socket.timeout("timed out"))):
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(smoke_runner.TransportTimeout):
                    self.call(error)

    def test_network_error_message_has_no_secret(self):
        with self.assertRaises(smoke_runner.TransportError) as caught:
            self.call(urllib.error.URLError(ConnectionRefusedError("refused")))
        self.assertNotIn(FAKE_KEY, str(caught.exception))

    def test_http_error_returns_status_instead_of_raising(self):
        error = urllib.error.HTTPError("https://example.invalid/v1", 429, "Too Many Requests",
                                       {"retry-after": "30"}, io.BytesIO(b'{"error": "rate"}'))
        status, headers, body = self.call(error)
        self.assertEqual(status, 429)
        self.assertEqual(body, b'{"error": "rate"}')


if __name__ == "__main__":
    unittest.main()
