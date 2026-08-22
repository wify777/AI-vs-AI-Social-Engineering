"""Unified logging for all AgentTrust events"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class AgentLogger:
    """Unified logging for all AgentTrust events"""

    def __init__(self, log_dir: str = "sandbox/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.attacks_log = self.log_dir / "attacks.jsonl"
        self.benign_log = self.log_dir / "benign.jsonl"
        self.errors_log = self.log_dir / "errors.jsonl"

    def log_attack_run(self, run_data: Dict[str, Any]) -> None:
        """Log a complete attack scenario"""
        assert run_data.get("tool_executed") is not None, "tool_executed required"
        run_data["timestamp"] = run_data.get("timestamp", datetime.utcnow().isoformat() + "Z")

        with open(self.attacks_log, "a") as f:
            f.write(json.dumps(run_data) + "\n")

    def log_benign_run(self, run_data: Dict[str, Any]) -> None:
        """Log a benign/control scenario"""
        run_data["timestamp"] = run_data.get("timestamp", datetime.utcnow().isoformat() + "Z")

        with open(self.benign_log, "a") as f:
            f.write(json.dumps(run_data) + "\n")

    def log_error(self, error_data: Dict[str, Any]) -> None:
        """Log errors for debugging"""
        error_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        with open(self.errors_log, "a") as f:
            f.write(json.dumps(error_data) + "\n")

    def read_attack_log(self) -> list:
        """Read all attack logs (for analysis)"""
        if not self.attacks_log.exists():
            return []

        results = []
        with open(self.attacks_log, "r") as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        return results

    def read_benign_log(self) -> list:
        """Read all benign logs"""
        if not self.benign_log.exists():
            return []

        results = []
        with open(self.benign_log, "r") as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        return results
