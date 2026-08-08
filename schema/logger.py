"""
Writes one JSONL log line per agent turn, matching schema/log_schema.json.

Usage:
    from schema.logger import log_turn and then write all the parameters for that function like presented below:

    log_turn(
        log_path="logs/run_2026-08-08_0001.jsonl",
        run_id="run_2026-08-08_0001",
        config_hash="a1b2c3",
        model_string="gemini-2.0-flash-001",
        payload_id="authority_spoof_003",
        condition="no_defense",
        repetition=1,
        turn_number=1,
        agent_role="parser",
        messages=[{"role": "user", "content": "..."}],
        tool_calls=[],
        latency_ms=842,
        tokens_input=120,
        tokens_output=45,
    )
"""

import json
import os
from datetime import datetime, timezone


def log_turn(
    log_path,
    run_id,
    config_hash,
    model_string,
    payload_id,
    condition,
    repetition,
    turn_number,
    agent_role,
    messages,
    tool_calls,
    latency_ms,
    tokens_input,
    tokens_output,
):

    entry = {
        "run_id": run_id,
        "config_hash": config_hash,
        "model_string": model_string,
        "run_date": datetime.now(timezone.utc).isoformat(),
        "payload_id": payload_id,
        "condition": condition,
        "repetition": repetition,
        "turn_number": turn_number,
        "agent_role": agent_role,
        "messages": messages,
        "tool_calls": tool_calls,
        "latency_ms": latency_ms,
        "tokens": {
            "input": tokens_input,
            "output": tokens_output,
        },
    }

    # Ensures that folder already exists before writing
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_log(log_path):
    entries = []
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
