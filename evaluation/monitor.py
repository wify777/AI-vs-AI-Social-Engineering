"""
Monitor experiment progress in real-time.

Usage:
    python evaluation/monitor.py  # Show current progress
    python evaluation/monitor.py --watch  # Auto-update every 10s
"""

import json
import time
import argparse
from pathlib import Path
from datetime import datetime


class ProgressMonitor:
    """Monitor experiment queue progress"""

    def __init__(self):
        self.attacks_log = Path("sandbox/logs/attacks.jsonl")
        self.checkpoint_file = Path("evaluation/checkpoint.json")

    def count_completed_runs(self) -> int:
        """Count completed runs from logs"""
        if not self.attacks_log.exists():
            return 0

        count = 0
        with open(self.attacks_log, "r") as f:
            for line in f:
                if line.strip():
                    count += 1

        return count

    def load_checkpoint(self) -> dict:
        """Load current checkpoint"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                return json.load(f)
        return {}

    def compute_asr_live(self) -> float:
        """Compute live ASR from current logs"""
        if not self.attacks_log.exists():
            return 0.0

        total = 0
        successes = 0

        with open(self.attacks_log, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        log = json.loads(line)
                        total += 1
                        if log.get("outcome", {}).get("tool_executed", False):
                            successes += 1
                    except:
                        pass

        if total == 0:
            return 0.0

        return (successes / total) * 100

    def print_status(self):
        """Print current status"""
        checkpoint = self.load_checkpoint()
        completed = self.count_completed_runs()
        asr = self.compute_asr_live()

        total_jobs = checkpoint.get("total_jobs", 720)
        progress_pct = (completed / total_jobs * 100) if total_jobs > 0 else 0

        print(f"\n{'='*70}")
        print(f"EXPERIMENT PROGRESS")
        print(f"{'='*70}\n")

        print(f"Completed runs: {completed}/{total_jobs} ({progress_pct:.1f}%)")
        print(f"Current ASR: {asr:.1f}%")
        print(f"Last update: {checkpoint.get('timestamp', 'never')}")

        if progress_pct > 0:
            estimated_total_time = completed / progress_pct * 100 / 60  # rough estimate
            remaining_time = estimated_total_time - (completed / 60)
            print(f"Estimated remaining time: {remaining_time:.1f} hours")

        print(f"\n{'='*70}\n")

    def watch(self, interval: int = 10):
        """Continuously monitor with updates"""
        print(f"Watching progress (update every {interval}s)...")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                self.print_status()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n✅ Monitoring stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor experiment progress")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", type=int, default=10, help="Update interval (seconds)")
    args = parser.parse_args()

    monitor = ProgressMonitor()

    if args.watch:
        monitor.watch(interval=args.interval)
    else:
        monitor.print_status()
