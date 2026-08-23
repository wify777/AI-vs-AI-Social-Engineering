"""
Run all models sequentially with monitoring and recovery.

Usage:
    python evaluation/run_all_models.py --local-only   # M5 only
    python evaluation/run_all_models.py --api-only     # M6 only
    python evaluation/run_all_models.py                # M5 + M6
"""

import subprocess
import json
import time
import argparse
import os
from datetime import datetime
from pathlib import Path


class ModelRunner:
    """Run experiments for all models"""

    LOCAL_MODELS = ["mistral:7b-instruct-q4_K_M"]
    API_MODELS = [
        # Groq models
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
        "allam-2-7b",
        # Google Gemini models
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        # Cerebras models
        "llama-3.3-70b",
    ]

    def __init__(self):
        self.results = []

    def run_model(self, model: str) -> bool:
        """Run experiment for single model"""
        print(f"\n{'='*70}")
        print(f"STARTING: {model}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")

        cmd = [
            "python3",
            "evaluation/run_experiments.py",
            "--model",
            model,
            "--benchmark",
            "benchmark/benchmark.json",
        ]

        start_time = time.time()

        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
            elapsed = time.time() - start_time

            status = "SUCCESS"
            self.results.append(
                {
                    "model": model,
                    "status": status,
                    "elapsed_seconds": elapsed,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            print(f"✅ {model} COMPLETE in {elapsed/3600:.1f} hours")
            return True

        except subprocess.CalledProcessError as e:
            elapsed = time.time() - start_time

            status = "FAILED"
            self.results.append(
                {
                    "model": model,
                    "status": status,
                    "error": str(e),
                    "elapsed_seconds": elapsed,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            print(f"❌ {model} FAILED after {elapsed/3600:.1f} hours")
            if e.stderr:
                print(f"Error: {e.stderr}")
            return False

    def run_all(self, local_only: bool = False, api_only: bool = False):
        """Run all models"""
        models_to_run = []

        if not api_only:
            models_to_run.extend(self.LOCAL_MODELS)

        if not local_only:
            models_to_run.extend(self.API_MODELS)

        print(f"\n{'='*70}")
        print(f"M5-M6 EXECUTION PLAN")
        print(f"{'='*70}")
        print(f"Models to run: {len(models_to_run)}")
        for m in models_to_run:
            print(f"  - {m}")
        print(f"{'='*70}\n")

        for i, model in enumerate(models_to_run, 1):
            print(f"\n[{i}/{len(models_to_run)}] Running {model}...")

            success = self.run_model(model)

            if not success:
                print(f"⚠️  {model} failed. Continuing to next model...")
                continue

            # Save intermediate results
            self.save_results()

        self.print_summary()

    def save_results(self):
        """Save execution results"""
        output_file = "results/execution_log.json"
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

    def print_summary(self):
        """Print final summary"""
        print(f"\n{'='*70}")
        print(f"EXECUTION SUMMARY")
        print(f"{'='*70}\n")

        for result in self.results:
            status_icon = "✅" if result["status"] == "SUCCESS" else "❌"
            hours = result.get("elapsed_seconds", 0) / 3600
            print(f"{status_icon} {result['model']:20s} | {hours:5.1f}h | {result['status']}")

        completed = sum(1 for r in self.results if r["status"] == "SUCCESS")
        total = len(self.results)

        print(f"\n{'='*70}")
        print(f"TOTAL: {completed}/{total} models completed")
        print(f"All results in: sandbox/logs/attacks.jsonl")
        print(f"Execution log: results/execution_log.json")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all models")
    parser.add_argument("--local-only", action="store_true", help="Run local models only (M5)")
    parser.add_argument("--api-only", action="store_true", help="Run API models only (M6)")
    args = parser.parse_args()

    runner = ModelRunner()
    runner.run_all(local_only=args.local_only, api_only=args.api_only)
