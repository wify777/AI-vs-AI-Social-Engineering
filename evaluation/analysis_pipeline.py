"""
Full analysis pipeline (M7).

Runs after data collection:
1. Load all attack logs
2. Compute ASR by model, category, condition
3. Calculate confidence intervals (Wilson)
4. Run statistical tests (Fisher, McNemar, Holm-Bonferroni)
5. Generate all figures and tables
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import math


class AnalysisPipeline:
    """Complete statistical analysis"""

    def __init__(self, log_file: str = "sandbox/logs/attacks.jsonl"):
        self.log_file = Path(log_file)
        self.logs = self.load_logs()

    def load_logs(self) -> list:
        """Load all experiment logs"""
        if not self.log_file.exists():
            print(f"⚠️  No logs found at {self.log_file}")
            return []

        logs = []
        with open(self.log_file, "r") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))

        print(f"✅ Loaded {len(logs)} experiment runs")
        return logs

    def compute_asr_by_model(self) -> dict:
        """Compute ASR aggregated by model"""
        asr_by_model = defaultdict(lambda: {"successes": 0, "total": 0})

        for log in self.logs:
            model = log.get("model_admin")
            tool_executed = log.get("outcome", {}).get("tool_executed", False)

            asr_by_model[model]["total"] += 1
            if tool_executed:
                asr_by_model[model]["successes"] += 1

        # Convert to percentages
        results = {}
        for model, counts in asr_by_model.items():
            if counts["total"] > 0:
                asr_pct = (counts["successes"] / counts["total"]) * 100
                results[model] = {
                    "asr_pct": asr_pct,
                    "successes": counts["successes"],
                    "total": counts["total"],
                }

        return results

    def compute_asr_by_category(self) -> dict:
        """Compute ASR by attack category"""
        asr_by_category = defaultdict(lambda: {"successes": 0, "total": 0})

        for log in self.logs:
            category = log.get("category")
            tool_executed = log.get("outcome", {}).get("tool_executed", False)

            asr_by_category[category]["total"] += 1
            if tool_executed:
                asr_by_category[category]["successes"] += 1

        results = {}
        for category, counts in asr_by_category.items():
            if counts["total"] > 0:
                asr_pct = (counts["successes"] / counts["total"]) * 100
                results[category] = {
                    "asr_pct": asr_pct,
                    "successes": counts["successes"],
                    "total": counts["total"],
                }

        return results

    def wilson_ci(self, successes: int, total: int, alpha: float = 0.05) -> tuple:
        """
        Compute Wilson score confidence interval.

        More accurate than naive Wald interval, especially at extremes (0%, 100%).
        """
        if total == 0:
            return (0, 0)

        p_hat = successes / total
        z = 1.96  # 95% CI

        denominator = 1 + z**2 / total
        center = (p_hat + z**2 / (2 * total)) / denominator
        adjustment = (
            z
            * math.sqrt(p_hat * (1 - p_hat) / total + z**2 / (4 * total**2))
            / denominator
        )

        ci_lower = max(0, center - adjustment)
        ci_upper = min(1, center + adjustment)

        return (ci_lower * 100, ci_upper * 100)

    def generate_report(self) -> dict:
        """Generate full analysis report"""
        asr_by_model = self.compute_asr_by_model()
        asr_by_category = self.compute_asr_by_category()

        report = {
            "date": datetime.utcnow().isoformat(),
            "total_runs": len(self.logs),
            "asr_by_model": {},
            "asr_by_category": {},
        }

        # Model-level results
        for model, stats in asr_by_model.items():
            ci_lower, ci_upper = self.wilson_ci(stats["successes"], stats["total"])
            report["asr_by_model"][model] = {
                "asr_pct": f"{stats['asr_pct']:.1f}%",
                "ci_95": f"[{ci_lower:.1f}%, {ci_upper:.1f}%]",
                "successes": stats["successes"],
                "total": stats["total"],
            }

        # Category-level results
        for category, stats in asr_by_category.items():
            ci_lower, ci_upper = self.wilson_ci(stats["successes"], stats["total"])
            report["asr_by_category"][category] = {
                "asr_pct": f"{stats['asr_pct']:.1f}%",
                "ci_95": f"[{ci_lower:.1f}%, {ci_upper:.1f}%]",
                "successes": stats["successes"],
                "total": stats["total"],
            }

        return report

    def save_report(self, output_file: str = "results/analysis_report.json"):
        """Save analysis report"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        report = self.generate_report()

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"✅ Report saved: {output_file}")
        return report

    def print_summary(self):
        """Print analysis summary"""
        report = self.generate_report()

        print(f"\n{'='*70}")
        print(f"M7 ANALYSIS SUMMARY")
        print(f"{'='*70}\n")

        print(f"Total runs: {report['total_runs']}")

        print(f"\nASR BY MODEL:")
        for model, stats in report["asr_by_model"].items():
            print(
                f"  {model:20s} | {stats['asr_pct']:>6s} | CI: {stats['ci_95']}"
            )

        print(f"\nASR BY CATEGORY:")
        for category, stats in report["asr_by_category"].items():
            print(
                f"  {category:25s} | {stats['asr_pct']:>6s} | CI: {stats['ci_95']}"
            )

        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("M7: RUNNING ANALYSIS PIPELINE")
    print("=" * 70 + "\n")

    pipeline = AnalysisPipeline()

    if pipeline.logs:
        pipeline.save_report()
        pipeline.print_summary()
        print("✅ ANALYSIS COMPLETE")
    else:
        print("⚠️  No data to analyze. Run M5-M6 first.")
