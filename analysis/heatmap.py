"""
Generate main heatmap: ASR by model × attack category.

This is THE central figure for the paper:
- X-axis: 4 attack categories (Authority, Urgency, Data, Gaslighting)
- Y-axis: 5 models (small to large)
- Color: ASR (% of attacks that succeeded)
  - Red = high ASR (vulnerable)
  - Green = low ASR (robust)
"""

import json
from pathlib import Path
from collections import defaultdict
from statistics import mean


class HeatmapGenerator:
    """Generate ASR heatmap from logs"""

    def __init__(self, log_file: str = "sandbox/logs/attacks_synthetic.jsonl"):
        self.log_file = log_file
        self.data = self.load_logs()

    def load_logs(self) -> list:
        """Load all attack logs"""
        if not Path(self.log_file).exists():
            print(f"⚠️  File not found: {self.log_file}")
            return []

        logs = []
        with open(self.log_file, "r") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))

        print(f"✅ Loaded {len(logs)} attack runs")
        return logs

    def compute_asr_matrix(self) -> dict:
        """
        Compute ASR for each (model, category) pair.

        Returns:
        {
            "llama2:7b": {
                "Authority Spoofing": 0.45,
                "Artificial Urgency": 0.52,
                ...
            },
            ...
        }
        """
        asr_matrix = defaultdict(
            lambda: defaultdict(lambda: {"successes": 0, "total": 0})
        )

        for log in self.data:
            model = log.get("model_admin")
            category = log.get("category")
            tool_executed = log.get("outcome", {}).get("tool_executed", False)

            asr_matrix[model][category]["total"] += 1
            if tool_executed:
                asr_matrix[model][category]["successes"] += 1

        # Compute percentages
        asr_percentages = {}
        for model, categories in asr_matrix.items():
            asr_percentages[model] = {}
            for category, counts in categories.items():
                if counts["total"] > 0:
                    asr_pct = (counts["successes"] / counts["total"]) * 100
                    asr_percentages[model][category] = asr_pct

        return asr_percentages

    def print_heatmap_ascii(self):
        """Print ASR heatmap as ASCII table"""
        asr_dict = self.compute_asr_matrix()

        # Order models (small to large)
        model_order = [
            "llama2:7b",
            "mistral:7b",
            "gemini-2.0-flash",
            "llama-3.1-70b",
            "mistral-nemo",
        ]

        # Order categories
        category_order = [
            "Authority Spoofing",
            "Artificial Urgency",
            "Data Spoofing",
            "Gaslighting",
        ]

        print("\n" + "=" * 90)
        print("ATTACK SUCCESS RATE (ASR) HEATMAP")
        print("=" * 90)
        print("\nFormat: ASR % (colored for vulnerability)")
        print("Legend: 0-20% (🟢 green) | 20-40% (🟡 yellow) | 40-60% (🟠 orange) | 60-100% (🔴 red)\n")

        # Print header
        header = "Model".ljust(20) + " | " + " | ".join([c[:12].center(12) for c in category_order])
        print(header)
        print("-" * 90)

        # Print rows
        for model in model_order:
            if model in asr_dict:
                row_data = [f"{asr_dict[model].get(cat, 0):6.1f}%" for cat in category_order]
                row_str = model.ljust(20) + " | " + " | ".join(
                    [v.center(12) for v in row_data]
                )
                print(row_str)
            else:
                print(model.ljust(20) + " | " + " | ".join(["  -  ".center(12) for _ in category_order]))

        print("=" * 90)

    def save_heatmap_data(self, output_path: str = "results/heatmap_asr_data.json"):
        """Save heatmap data as JSON"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        asr_dict = self.compute_asr_matrix()

        with open(output_path, "w") as f:
            json.dump(asr_dict, f, indent=2)

        print(f"✅ Heatmap data saved: {output_path}")

    def print_summary(self):
        """Print summary statistics"""
        asr_dict = self.compute_asr_matrix()

        print("\n" + "=" * 70)
        print("ASR SUMMARY BY MODEL")
        print("=" * 70)

        for model in [
            "llama2:7b",
            "mistral:7b",
            "gemini-2.0-flash",
            "llama-3.1-70b",
            "mistral-nemo",
        ]:
            if model in asr_dict:
                avg_asr = mean(list(asr_dict[model].values())) if asr_dict[model] else 0
                print(f"{model:20s} | Avg ASR: {avg_asr:5.1f}%")

        print("\n" + "=" * 70)
        print("ASR SUMMARY BY CATEGORY")
        print("=" * 70)

        for category in ["Authority Spoofing", "Artificial Urgency", "Data Spoofing", "Gaslighting"]:
            category_asr_values = []
            for model in asr_dict:
                if category in asr_dict[model]:
                    category_asr_values.append(asr_dict[model][category])

            if category_asr_values:
                avg_asr = mean(category_asr_values)
                print(f"{category:25s} | Avg ASR: {avg_asr:5.1f}%")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("GENERATING HEATMAP FROM SYNTHETIC DATA")
    print("=" * 70 + "\n")

    hm = HeatmapGenerator(log_file="sandbox/logs/attacks_synthetic.jsonl")

    if hm.data:
        hm.print_heatmap_ascii()
        hm.save_heatmap_data()
        hm.print_summary()
        print("\n✅ HEATMAP GENERATION COMPLETE")
    else:
        print("⚠️  No data found. Run synthetic_data.py first.")

    print("=" * 70)
