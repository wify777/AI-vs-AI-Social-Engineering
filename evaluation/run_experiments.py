"""
Main experiment runner with error handling and checkpoint recovery.

Usage:
    python evaluation/run_experiments.py --model llama2:7b --benchmark benchmark/benchmark.json
    python evaluation/run_experiments.py --dry-run  # Run 1 payload per model
"""

import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from evaluation.experiment_queue import ExperimentQueue, ExperimentJob, RateLimiter
from sandbox.logger import AgentLogger


class ExperimentRunner:
    """Run attacks and log results"""

    def __init__(self, model: str, provider: str = "auto"):
        self.model = model
        self.provider = provider
        self.logger = AgentLogger()
        self.rate_limiter = RateLimiter()

        # Try to import agents, but fail gracefully if dependencies missing
        try:
            from sandbox.agents.parser_agent import ParserAgent
            from sandbox.agents.admin_agent import AdminAgent
            from sandbox.bus import MessageBus

            self.parser = ParserAgent(model=model, provider=self._infer_provider())
            self.admin = AdminAgent(model=model, provider=self._infer_provider())
            self.bus = MessageBus()
            self.agents_available = True
        except ImportError as e:
            print(f"⚠️  Warning: Agents not available ({e})")
            self.agents_available = False

    def _infer_provider(self) -> str:
        """Infer provider from model name"""
        if ":" in self.model:  # ollama format (e.g., mistral:7b)
            return "ollama"
        elif "gemini" in self.model.lower():
            return "google"
        elif any(prefix in self.model.lower() for prefix in ["openai/", "qwen/", "allam-", "groq", "llama-3"]):
            return "groq"
        else:
            return "api"

    def load_payloads(self, benchmark_file: str) -> List[Dict]:
        """Load attack payloads"""
        with open(benchmark_file, "r") as f:
            payloads = json.load(f)

        print(f"✅ Loaded {len(payloads)} payloads from {benchmark_file}")
        return payloads

    def run_single_attack(
        self, payload: Dict, condition: str = "baseline", rep: int = 1
    ) -> Dict:
        """Run one attack and return result"""
        self.rate_limiter.wait_if_needed()

        if not self.agents_available:
            raise RuntimeError(
                'Agents not available! Cannot proceed. Check imports. '
                'Ensure sandbox/agents/ and sandbox/bus.py are properly configured.'
            )

        try:
            result = self.bus.orchestrate_attack(
                payload=payload, parser=self.parser, admin=self.admin, condition=condition, repetition=rep
            )
            return result

        except Exception as e:
            error_log = {
                "payload_id": payload.get("id", "unknown"),
                "model": self.model,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            self.logger.log_error(error_log)
            raise

    def run_queue(self, queue: ExperimentQueue, dry_run: bool = False) -> None:
        """Process experiment queue"""
        stats = queue.stats()
        total = stats["total"]

        print(f"\n{'='*70}")
        print(f"Running {total} experiments")
        print(f"Model: {self.model} ({self._infer_provider()})")
        print(f"Resume from: {queue.load_checkpoint()}")
        print(f"{'='*70}\n")

        start_idx = queue.load_checkpoint()

        for i, job in enumerate(queue.jobs[start_idx:], start=start_idx):
            if dry_run and i >= start_idx + 1:
                print("✅ Dry-run complete (1 payload tested)")
                break

            try:
                print(f"[{i+1}/{total}] {job.payload_id} | " f"{job.category} | {job.condition}")

                # Execute
                result = self.run_single_attack(
                    payload=job.result or {}, condition=job.condition, rep=job.repetition
                )

                # Mark success
                queue.mark_completed(job.job_id, result)
                queue.save_checkpoint(i + 1, total)

                # Print ASR result
                asr = result.get("outcome", {}).get("asr", 0)
                print(f"  → ASR: {'✅ SUCCESS' if asr else '✅ BLOCKED'}\n")

            except Exception as e:
                print(f"  → ❌ ERROR: {str(e)}\n")
                queue.mark_failed(job.job_id, str(e))
                queue.save_checkpoint(i, total)

        # Final stats
        final_stats = queue.stats()
        print(f"\n{'='*70}")
        print(f"FINAL STATS")
        print(f"{'='*70}")
        print(f"Total: {final_stats['total']}")
        print(f"Completed: {final_stats['completed']} ({final_stats['progress_pct']:.1f}%)")
        print(f"Failed: {final_stats['failed']}")
        print(f"Pending: {final_stats['pending']}")
        print(f"Rate limiter: {self.rate_limiter.status()}")


def main():
    parser = argparse.ArgumentParser(description="Run AgentTrust experiments")
    parser.add_argument("--model", type=str, default="llama2:7b", help="Model to test")
    parser.add_argument(
        "--benchmark", type=str, default="benchmark/benchmark.json", help="Benchmark file"
    )
    parser.add_argument("--dry-run", action="store_true", help="Run 1 payload only")
    args = parser.parse_args()

    runner = ExperimentRunner(model=args.model)
    queue = ExperimentQueue(model_name=args.model)

    # Load payloads if queue empty
    if not queue.jobs:
        payloads = runner.load_payloads(args.benchmark)
        conditions = ["baseline", "with_source_text", "with_defense_mechanism"]

        job_id = 0
        for payload in payloads:
            for condition in conditions:
                for rep in [1, 2, 3]:
                    job = ExperimentJob(
                        job_id=f"job_{job_id:06d}",
                        payload_id=payload["id"],
                        model_admin=args.model,
                        model_parser=args.model,
                        category=payload.get("category", "Unknown"),
                        condition=condition,
                        repetition=rep,
                        result=payload,
                    )
                    queue.add_job(job)
                    job_id += 1

    # Run experiments
    runner.run_queue(queue, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
