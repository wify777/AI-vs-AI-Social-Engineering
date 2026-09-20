"""
Generate publication-quality heatmap: ASR by model x attack category (v3 final).

- X-axis: 4 attack categories
- Y-axis: 6 models, ordered by overall ASR
- Color: sequential single-hue ramp (magnitude encoding, CVD-safe)
- Scale: clipped to the observed data range, not 0-100, so real contrast is visible
- Cells annotate ASR% with k/n; row labels carry each model's sample size
"""

import json
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path
from collections import defaultdict

MODEL_ORDER = [
    "openai/gpt-oss-20b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "openai/gpt-oss-120b",
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "minimax/minimax-m3:free",
]

# Shortened labels for the figure; full ids stay in the data
MODEL_LABELS = {
    "openai/gpt-oss-20b": "gpt-oss-20b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": "nemotron-3-nano-30b",
    "openai/gpt-oss-120b": "gpt-oss-120b",
    "gemini-3.6-flash": "gemini-3.6-flash",
    "gemini-flash-latest": "gemini-flash-latest",
    "minimax/minimax-m3:free": "minimax-m3",
}

# Models whose runs were cut short by API rate limiting
PARTIAL = {"gemini-3.6-flash", "gemini-flash-latest"}

CATEGORY_ORDER = [
    "Authority Spoofing",
    "Artificial Urgency",
    "Data Spoofing",
    "Gaslighting",
]


class HeatmapGenerator:
    """Build the ASR matrix from the experiment log and render it."""

    def __init__(self, log_file: str = "sandbox/logs/attacks.jsonl"):
        self.log_file = log_file
        self.data = self.load_logs()

    def load_logs(self) -> list:
        if not Path(self.log_file).exists():
            print(f"File not found: {self.log_file}")
            return []
        logs = []
        with open(self.log_file) as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        print(f"Loaded {len(logs)} attack runs")
        return logs

    @staticmethod
    def _executed(log: dict) -> bool:
        return bool(log.get("outcome", {}).get("tool_executed", False))

    def compute_matrix(self):
        """Return (asr_pct, counts, model_totals) keyed by model then category."""
        cells = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # [n, k]
        for log in self.data:
            model = log.get("model_admin")
            category = log.get("category")
            cells[model][category][0] += 1
            if self._executed(log):
                cells[model][category][1] += 1

        asr, counts, totals = {}, {}, {}
        for model, cats in cells.items():
            asr[model], counts[model] = {}, {}
            totals[model] = sum(n for n, _ in cats.values())
            for cat, (n, k) in cats.items():
                asr[model][cat] = (k / n * 100) if n else 0.0
                counts[model][cat] = (k, n)
        return asr, counts, totals

    def overall_asr(self):
        n = len(self.data)
        k = sum(1 for log in self.data if self._executed(log))
        return (k / n * 100 if n else 0.0), k, n

    def print_ascii(self):
        asr, counts, totals = self.compute_matrix()
        pct, k, n = self.overall_asr()

        print("\n" + "=" * 96)
        print(f"ASR HEATMAP - v3 FINAL (n={n}, overall ASR {pct:.2f}%)")
        print("=" * 96)
        header = "Model".ljust(24) + "n".rjust(6) + "  " + "".join(c[:13].rjust(15) for c in CATEGORY_ORDER)
        print(header)
        print("-" * 96)
        for model in MODEL_ORDER:
            if model not in asr:
                continue
            label = MODEL_LABELS.get(model, model)[:23]
            row = label.ljust(24) + str(totals[model]).rjust(6) + "  "
            for cat in CATEGORY_ORDER:
                v = asr[model].get(cat, 0.0)
                kk, nn = counts[model].get(cat, (0, 0))
                row += f"{v:5.1f}% ({kk}/{nn})".rjust(15)
            print(row)
        print("=" * 96)
        print(f"OVERALL: {pct:.2f}%  ({k}/{n})")
        print("=" * 96)

    def generate_figure(self, output_path: str = "results/figures/heatmap_v3_final.png"):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        asr, counts, totals = self.compute_matrix()
        pct, k_tot, n_tot = self.overall_asr()

        models = [m for m in MODEL_ORDER if m in asr]
        matrix = np.zeros((len(models), len(CATEGORY_ORDER)))
        for i, m in enumerate(models):
            for j, c in enumerate(CATEGORY_ORDER):
                matrix[i, j] = asr[m].get(c, 0.0)

        # Scale to the data, not to 0-100: at vmax=100 every cell here reads as one flat tone.
        vmax = max(5.0, math.ceil(matrix.max() / 5.0) * 5.0)

        mpl.rcParams["font.family"] = "DejaVu Sans"
        mpl.rcParams["font.size"] = 12

        fig, ax = plt.subplots(figsize=(14, 8), dpi=300)

        # Single-hue sequential ramp: ASR is magnitude, not polarity.
        # Avoids the red-green rainbow, which misencodes magnitude and fails for CVD readers.
        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=vmax)

        ax.set_xticks(np.arange(len(CATEGORY_ORDER)))
        ax.set_yticks(np.arange(len(models)))
        ax.set_xticklabels(CATEGORY_ORDER, fontsize=12)

        ylabels = []
        for m in models:
            label = MODEL_LABELS.get(m, m)
            mark = "*" if m in PARTIAL else ""
            ylabels.append(f"{label}{mark}\n(n={totals[m]})")
        ax.set_yticklabels(ylabels, fontsize=11)

        ax.set_xlabel("Attack Category", fontsize=13, labelpad=12)
        ax.set_ylabel("Model (ordered by overall ASR)", fontsize=13, labelpad=12)
        ax.set_title(
            f"AgentTrust v3: Attack Success Rate by Model x Category\n"
            f"n={n_tot} experiments, overall ASR {pct:.2f}% ({k_tot}/{n_tot})",
            fontsize=15, pad=18,
        )

        # 2px surface gap between cells so adjacent fills stay separable
        ax.set_xticks(np.arange(len(CATEGORY_ORDER) + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(len(models) + 1) - 0.5, minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.tick_params(which="minor", bottom=False, left=False)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Annotate value + k/n; flip ink to white only where the fill is dark enough
        for i, m in enumerate(models):
            for j, c in enumerate(CATEGORY_ORDER):
                v = matrix[i, j]
                kk, nn = counts[m].get(c, (0, 0))
                ax.text(j, i, f"{v:.1f}%\n{kk}/{nn}",
                        ha="center", va="center",
                        color="white" if v > vmax * 0.6 else "#1a1a1a",
                        fontsize=11)

        cbar = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
        cbar.set_label("Attack Success Rate (%)", fontsize=12, labelpad=12)
        cbar.ax.tick_params(labelsize=11)
        cbar.outline.set_visible(False)

        fig.text(0.01, 0.015,
                 "* run truncated by Google API rate limiting; interpret with the wider interval in mind",
                 fontsize=9, color="#555555")

        plt.tight_layout(rect=(0, 0.03, 1, 1))
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Figure saved: {output_path}")
        plt.close()

    def save_data(self, output_path: str = "results/heatmap_asr_data.json"):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        asr, counts, totals = self.compute_matrix()
        pct, k, n = self.overall_asr()
        payload = {
            "overall": {"asr": pct, "successes": k, "n": n},
            "models": {
                m: {
                    "n": totals[m],
                    "partial_run": m in PARTIAL,
                    "categories": {
                        c: {"asr": asr[m].get(c, 0.0),
                            "successes": counts[m].get(c, (0, 0))[0],
                            "n": counts[m].get(c, (0, 0))[1]}
                        for c in CATEGORY_ORDER
                    },
                }
                for m in MODEL_ORDER if m in asr
            },
        }
        with open(output_path, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"Data saved: {output_path}")


if __name__ == "__main__":
    hm = HeatmapGenerator()
    if hm.data:
        hm.print_ascii()
        hm.save_data()
        hm.generate_figure("results/figures/heatmap_v3_final.png")
        hm.generate_figure("results/figures/heatmap_baseline_v1.png")
    else:
        print("No data found. Run the experiment runner first.")
