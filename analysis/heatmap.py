"""
Generate publication-quality heatmap: ASR by model × attack category (v3).

Creates a high-resolution figure suitable for academic publication:
- X-axis: 4 attack categories (Authority, Urgency, Data, Gaslighting)
- Y-axis: 10 models (Groq, Google, OpenRouter)
- Color: ASR (% of attacks that succeeded) with RdYlGn_r colormap
  - Red = high ASR (vulnerable)
  - Green = low ASR (robust)
- Sample sizes: n=X shown under each model
- Overall ASR: shown in corner
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

    def compute_asr_matrix(self) -> tuple:
        """
        Compute ASR for each (model, category) pair.

        Returns:
        (asr_dict, sample_counts)
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

        # Compute percentages and sample counts
        asr_percentages = {}
        sample_counts = {}

        for model, categories in asr_matrix.items():
            asr_percentages[model] = {}
            total_samples = sum(c["total"] for c in categories.values())
            sample_counts[model] = total_samples

            for category, counts in categories.items():
                if counts["total"] > 0:
                    asr_pct = (counts["successes"] / counts["total"]) * 100
                    asr_percentages[model][category] = asr_pct

        return asr_percentages, sample_counts

    def print_heatmap_ascii(self):
        """Print ASR heatmap as ASCII table (v3: 10 models)"""
        asr_dict, sample_counts = self.compute_asr_matrix()

        # Order models (by vulnerability, for v3)
        model_order = [
            "openai/gpt-oss-20b",
            "google/gemma-4-31b-it:free",
            "openai/gpt-oss-120b",
            "google/gemma-4-26b-a4b-it:free",
            "gemini-3.6-flash",
            "gemini-flash-latest",
            "meta-llama/llama-3.2-3b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "allam-2-7b",
            "qwen/qwen3.6-27b",
        ]

        # Order categories
        category_order = [
            "Authority Spoofing",
            "Artificial Urgency",
            "Data Spoofing",
            "Gaslighting",
        ]

        print("\n" + "=" * 120)
        print("ATTACK SUCCESS RATE (ASR) HEATMAP — v3 FINAL (n=2,731)")
        print("=" * 120)
        print("\nFormat: ASR % with sample size (n)")
        print("Legend: 0-5% (🟢 green) | 5-10% (🟡 yellow) | 10-20% (🟠 orange) | 20-100% (🔴 red)\n")

        # Print header
        header = "Model".ljust(40) + " | " + " | ".join([c[:10].center(10) for c in category_order])
        print(header)
        print("-" * 125)

        # Print rows
        for model in model_order:
            if model in asr_dict:
                n = sample_counts.get(model, 0)
                row_data = [f"{asr_dict[model].get(cat, 0):5.1f}%" for cat in category_order]
                row_str = f"{model[:40].ljust(40)} (n={n:3d}) | " + " | ".join(
                    [v.center(10) for v in row_data]
                )
                print(row_str)
            else:
                print(f"{model[:40].ljust(40)}         | " + " | ".join(["  -  ".center(10) for _ in category_order]))

        print("=" * 125)

        # Overall ASR
        total_success = sum(1 for log in self.data if log.get('tool_executed'))
        overall_asr = (total_success / len(self.data) * 100) if self.data else 0
        print(f"\nOVERALL ASR: {overall_asr:.2f}% ({total_success}/{len(self.data)})")
        print("=" * 125)

    def generate_figure(self, output_path: str = "results/figures/heatmap_v3_final.png"):
        """Generate publication-quality matplotlib figure (v3 Final: 10 models, 14x8 inches, 300 DPI)"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        asr_dict, sample_counts = self.compute_asr_matrix()

        # Model order (by vulnerability)
        model_order = [
            "openai/gpt-oss-20b",
            "google/gemma-4-31b-it:free",
            "openai/gpt-oss-120b",
            "google/gemma-4-26b-a4b-it:free",
            "gemini-3.6-flash",
            "gemini-flash-latest",
            "meta-llama/llama-3.2-3b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "allam-2-7b",
            "qwen/qwen3.6-27b",
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
        mpl.rcParams['font.size'] = 12

        # Create figure with publication size: 14x8 inches, 300 DPI
        fig, ax = plt.subplots(figsize=(14, 8), dpi=300)

        # Use RdYlGn_r colormap (red=vulnerable, green=robust)
        im = ax.imshow(matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=100)

        # Set ticks
        ax.set_xticks(np.arange(len(category_order)))
        ax.set_yticks(np.arange(len(model_order)))

        # Set labels with bold font (font size 12)
        ax.set_xticklabels(category_order, fontsize=12, fontweight='bold')

        # Model labels with sample size notation
        model_labels = [f"{model}\n(n={sample_counts.get(model, 0)})" for model in model_order]
        ax.set_yticklabels(model_labels, fontsize=11, fontweight='bold')

        # Axis labels
        ax.set_xlabel('Attack Category', fontsize=14, fontweight='bold', labelpad=15)
        ax.set_ylabel('Model', fontsize=14, fontweight='bold', labelpad=15)

        # Title with final v3 stats
        total_success = sum(1 for log in self.data if log.get('tool_executed'))
        overall_asr = (total_success / len(self.data) * 100) if self.data else 0
        title = f'AgentTrust v3: Attack Success Rate by Model × Category (n={len(self.data)}, Overall ASR={overall_asr:.2f}%)'
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

        # Add text annotations in each cell (bold, size 12)
        for i in range(len(model_order)):
            for j in range(len(category_order)):
                asr_val = matrix[i, j]
                # Choose text color based on background: dark text on light, light text on dark
                text_color = 'white' if asr_val > 50 else 'black'
                text = ax.text(j, i, f'{asr_val:.1f}%',
                             ha="center", va="center",
                             color=text_color, fontsize=12, fontweight='bold')

        # Colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Attack Success Rate (%)', fontsize=12, fontweight='bold', labelpad=15)
        cbar.ax.tick_params(labelsize=11)

        # Tight layout
        plt.tight_layout()

        # Save with high DPI (300 DPI for publication quality)
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Publication-quality figure saved: {output_path}")

        plt.close()

    def save_heatmap_data(self, output_path: str = "results/heatmap_asr_data.json"):
        """Save heatmap data as JSON"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        asr_dict, sample_counts = self.compute_asr_matrix()

        with open(output_path, "w") as f:
            json.dump(asr_dict, f, indent=2)

        print(f"✅ Heatmap data saved: {output_path}")

    def print_summary(self):
        """Print summary statistics (v3: 10 models)"""
        asr_dict, sample_counts = self.compute_asr_matrix()

        model_order = [
            "openai/gpt-oss-20b",
            "google/gemma-4-31b-it:free",
            "openai/gpt-oss-120b",
            "google/gemma-4-26b-a4b-it:free",
            "gemini-3.6-flash",
            "gemini-flash-latest",
            "meta-llama/llama-3.2-3b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "allam-2-7b",
            "qwen/qwen3.6-27b",
        ]

        print("\n" + "=" * 80)
        print("ASR SUMMARY BY MODEL (v3 FINAL)")
        print("=" * 80)

        for model in model_order:
            if model in asr_dict:
                avg_asr = mean(list(asr_dict[model].values())) if asr_dict[model] else 0
                n = sample_counts.get(model, 0)
                print(f"{model:45s} | n={n:3d} | Avg ASR: {avg_asr:6.2f}%")

        print("\n" + "=" * 80)
        print("ASR SUMMARY BY CATEGORY (v3 FINAL)")
        print("=" * 80)

        for category in ["Authority Spoofing", "Artificial Urgency", "Data Spoofing", "Gaslighting"]:
            category_asr_values = []
            for model in asr_dict:
                if category in asr_dict[model]:
                    category_asr_values.append(asr_dict[model][category])

            if category_asr_values:
                avg_asr = mean(category_asr_values)
                print(f"{category:40s} | Avg ASR: {avg_asr:6.2f}%")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("GENERATING PUBLICATION-QUALITY HEATMAP (v3 FINAL)")
    print("=" * 70 + "\n")

    hm = HeatmapGenerator(log_file="sandbox/logs/attacks.jsonl")

    if hm.data:
        hm.print_heatmap_ascii()
        hm.save_heatmap_data()

        # Generate v3 final heatmap (primary)
        print("\n📊 Generating heatmap_v3_final.png...")
        hm.generate_figure(output_path="results/figures/heatmap_v3_final.png")

        # Also update baseline v1 (legacy)
        print("\n📊 Updating heatmap_baseline_v1.png with v3 data...")
        hm.generate_figure(output_path="results/figures/heatmap_baseline_v1.png")

        hm.print_summary()
        print("\n✅ HEATMAP GENERATION COMPLETE")
        print("   - heatmap_v3_final.png: publication-ready (14x8\", 300 DPI)")
        print("   - heatmap_baseline_v1.png: updated with v3 data")
    else:
        print("⚠️  No data found. Run experiment runner first.")

    print("=" * 70)
