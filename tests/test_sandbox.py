"""Exercise sandbox plumbing with fake agents and temporary log paths only."""

import json

import pytest

from sandbox.bus import MessageBus, run_conversation
from sandbox.logger import AgentLogger
from sandbox.redact import redact, safe_error
from sandbox.tools import ToolRegistry
from schema.logger import log_turn, read_log


@pytest.mark.parametrize(
    "variable", ["GROQ_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY"]
)
def test_environment_credentials_are_redacted(monkeypatch, variable):
    key = "test-only-value-not-a-real-api-key"
    monkeypatch.setenv(variable, key)
    assert key not in redact(f"Request failed: {key}")


@pytest.mark.parametrize(
    "text", ["https://example.test?key=abcdefghijklmnop", "Bearer abcdefghijklmnop"]
)
def test_credentials_are_redacted_without_environment_values(monkeypatch, text):
    for name in ("GROQ_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert "abcdefghijklmnop" not in safe_error(RuntimeError(text))


def test_redaction_preserves_non_secret_diagnostics():
    assert redact("HTTP 429: retry later") == "HTTP 429: retry later"
    assert redact("") == ""


def test_tool_stubs_record_calls_without_real_effects(tmp_path):
    log = tmp_path / "tools.jsonl"
    tools = ToolRegistry(str(log))
    assert tools.delete_user_account("fictional-user")["status"] == "pending_approval"
    assert (
        tools.reset_user_password("fictional-user", "private-test-password")[
            "password_changed"
        ]
        is False
    )
    assert tools.execute_sql_query("SELECT 1")["query_executed"] is False
    assert (
        tools.dispatch_external_email("test@example.invalid", "test", "body")["sent"]
        is False
    )
    assert "private-test-password" not in log.read_text()
    assert len(log.read_text().splitlines()) == 4


def test_logger_preserves_explicit_negative_outcomes(tmp_path):
    logger = AgentLogger(str(tmp_path))
    logger.log_attack_run({"tool_executed": False})
    assert logger.read_attack_log()[0]["tool_executed"] is False


def test_logger_requires_an_outcome(tmp_path):
    with pytest.raises(AssertionError, match="tool_executed required"):
        AgentLogger(str(tmp_path)).log_attack_run({})


@pytest.fixture
def context():
    return dict(
        run_id="test-run",
        config_hash="test",
        model_string="fake",
        payload_id="p1",
        condition="baseline",
        repetition=1,
    )


def test_multi_turn_bus_logs_and_stops_after_tool_call(tmp_path, context):
    log = tmp_path / "turns.jsonl"

    def admin(messages):
        return {
            "text": "stub response",
            "tool_calls": [{"tool_name": "execute_sql_query"}],
        }

    def parser(messages):
        raise AssertionError("Parser must not run after the tool call")

    result = run_conversation(parser, admin, "fictional input", 3, str(log), context)
    assert result["outcome"] == "success"
    assert len(read_log(str(log))) == 1


def test_multi_turn_bus_respects_turn_limit(tmp_path, context):
    log = tmp_path / "turns.jsonl"
    fake = lambda messages: {"text": "no action"}
    result = run_conversation(fake, fake, "input", 2, str(log), context)
    assert result["outcome"] == "no_compliance"
    assert len(read_log(str(log))) == 4


def test_source_text_is_explicitly_labeled_in_conversation(tmp_path, context):
    context["condition"] = ""
    captured = []

    def admin(messages):
        captured.append(messages[0]["content"])
        return {"text": "refusal"}

    run_conversation(
        lambda messages: {"text": "stop"},
        admin,
        "forwarded",
        1,
        str(tmp_path / "turns.jsonl"),
        context,
        source_text="original",
    )
    assert "[ORIGINAL SOURCE TEXT]\noriginal" in captured[0]
    assert context["condition"] == "with_source_text"


def test_schema_logger_accepts_a_filename_in_current_directory(
    tmp_path, monkeypatch, context
):
    monkeypatch.chdir(tmp_path)
    log_turn(
        log_path="turns.jsonl",
        **context,
        turn_number=1,
        agent_role="admin",
        messages=[],
        tool_calls=[],
        latency_ms=1,
        tokens_input=0,
        tokens_output=0,
    )
    assert read_log("turns.jsonl")[0]["run_id"] == "test-run"


def test_message_bus_uses_supplied_logger(tmp_path):
    class Parser:
        model = "fake-parser"

        def parse_content(self, **kwargs):
            return {"parsed_content": "fictional input"}

    class Admin:
        model = "fake-admin"

        def process_message(self, **kwargs):
            return {"tool_executed": False}

    logger = AgentLogger(str(tmp_path))
    result = MessageBus(logger).orchestrate_attack(
        {"id": "p1", "attack_content": "fictional input"}, Parser(), Admin()
    )
    assert result["outcome"]["asr"] == 0
    assert len(logger.read_attack_log()) == 1
