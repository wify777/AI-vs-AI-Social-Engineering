"""
Generate publication-quality heatmap: ASR by model × attack category.

Creates a high-resolution figure suitable for academic publication:
- X-axis: 4 attack categories (Authority, Urgency, Data, Gaslighting)
- Y-axis: 4 models (by size)
- Color: ASR (% of attacks that succeeded) with RdYlGn_r colormap
  - Red = high ASR (vulnerable)
  - Green = low ASR (robust)
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path
from collections import defaultdict
from statistics import mean


class HeatmapGenerator:
    """Generate ASR heatmap from logs"""

    def __init__(self, log_file: str = "sandbox/logs/attacks.jsonl"):
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
            "openai/gpt-oss-20b": {
                "Authority Spoofing": 1.4,
                "Artificial Urgency": 0.0,
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
            tool_executed = log.get("tool_executed", False)

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
            "allam-2-7b",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
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
        header = "Model".ljust(25) + " | " + " | ".join([c[:12].center(12) for c in category_order])
        print(header)
        print("-" * 95)

        # Print rows
        for model in model_order:
            if model in asr_dict:
                row_data = [f"{asr_dict[model].get(cat, 0):6.1f}%" for cat in category_order]
                row_str = model.ljust(25) + " | " + " | ".join(
                    [v.center(12) for v in row_data]
                )
                print(row_str)
            else:
                print(model.ljust(25) + " | " + " | ".join(["  -  ".center(12) for _ in category_order]))

        print("=" * 95)

    def generate_figure(self, output_path: str = "results/figures/heatmap_baseline_v1.png"):
        """Generate publication-quality matplotlib figure"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        asr_dict = self.compute_asr_matrix()

        # Model order (small to large)
        model_order = [
            "allam-2-7b",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
        ]

        # Category order
        category_order = [
            "Authority Spoofing",
            "Artificial Urgency",
            "Data Spoofing",
            "Gaslighting",
        ]

        # Build matrix
        matrix = np.zeros((len(model_order), len(category_order)))
        for i, model in enumerate(model_order):
            for j, category in enumerate(category_order):
                matrix[i, j] = asr_dict.get(model, {}).get(category, 0)

        # Configure publication-quality font
        mpl.rcParams['font.family'] = 'DejaVu Sans'
        mpl.rcParams['font.size'] = 11

        # Create figure with specific size and DPI
        fig, ax = plt.subplots(figsize=(12, 8), dpi=300)

        # Use RdYlGn_r colormap (red=vulnerable, green=robust)
        im = ax.imshow(matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=100)

        # Set ticks
        ax.set_xticks(np.arange(len(category_order)))
        ax.set_yticks(np.arange(len(model_order)))

        # Set labels with bold font
        ax.set_xticklabels(category_order, fontsize=12, fontweight='bold')

        # Model labels with n=144 notation
        model_labels = [f"{model}\n(n=144)" for model in model_order]
        ax.set_yticklabels(model_labels, fontsize=12, fontweight='bold')

        # Axis labels
        ax.set_xlabel('Attack Category', fontsize=14, fontweight='bold', labelpad=15)
        ax.set_ylabel('Model (by Size)', fontsize=14, fontweight='bold', labelpad=15)

        # Title
        ax.set_title('Attack Success Rate by Model and Attack Category (n=576)',
                    fontsize=16, fontweight='bold', pad=20)

        # Add text annotations in each cell
        for i in range(len(model_order)):
            for j in range(len(category_order)):
                text = ax.text(j, i, f'{matrix[i, j]:.1f}%',
                             ha="center", va="center",
                             color="black", fontsize=13, fontweight='bold')

        # Colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Attack Success Rate (%)', fontsize=12, fontweight='bold', labelpad=15)
        cbar.ax.tick_params(labelsize=11)

        # Tight layout
        plt.tight_layout()

        # Save with high DPI
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Publication-quality figure saved: {output_path}")

        plt.close()

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
            "allam-2-7b",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
        ]:
            if model in asr_dict:
                avg_asr = mean(list(asr_dict[model].values())) if asr_dict[model] else 0
                print(f"{model:25s} | Avg ASR: {avg_asr:5.1f}%")

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
    print("GENERATING PUBLICATION-QUALITY HEATMAP")
    print("=" * 70 + "\n")

    hm = HeatmapGenerator(log_file="sandbox/logs/attacks.jsonl")

    if hm.data:
        hm.print_heatmap_ascii()
        hm.save_heatmap_data()
        hm.generate_figure(output_path="results/figures/heatmap_baseline_v1.png")
        hm.print_summary()
        print("\n✅ HEATMAP GENERATION COMPLETE")
    else:
        print("⚠️  No data found. Run experiment runner first.")

    print("=" * 70)
