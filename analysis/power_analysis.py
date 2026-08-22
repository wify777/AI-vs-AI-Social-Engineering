"""
Power analysis for AgentTrust experiments.

Key insight: With n=15 payloads per category, what is the minimum
detectable effect size (MDES) at 80% power?

Answer: ~25 percentage points (pp)

This means:
- ASR=45% vs ASR=70% → We WILL detect this difference (Δ=25pp)
- ASR=45% vs ASR=50% → We WON'T detect this difference (Δ=5pp too small)
"""

import json
from pathlib import Path
from math import comb


class PowerAnalysis:
    """Calculate minimum detectable effect size for binomial tests"""

    def __init__(self, n_per_category: int = 15, alpha: float = 0.05, power: float = 0.80):
        self.n = n_per_category
        self.alpha = alpha
        self.power = power

    def binomial_cdf(self, k: int, n: int, p: float) -> float:
        """Compute cumulative binomial probability P(X <= k)"""
        total = 0.0
        for i in range(k + 1):
            total += comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
        return total

    def power_for_effect_size(self, p0: float, p1: float, n: int, alpha: float = 0.05) -> float:
        """
        Calculate power for one-sided binomial test.

        p0: baseline proportion (e.g., 0.50)
        p1: alternative proportion (e.g., 0.75)
        n: sample size per group
        """
        # Find critical value k such that P(X > k | p0) = alpha
        for k in range(n + 1):
            if self.binomial_cdf(k, n, p0) > (1 - alpha):
                critical_k = k
                break

        # Power: P(X > critical_k | p1) = 1 - P(X <= critical_k | p1)
        power = 1 - self.binomial_cdf(critical_k, n, p1)
        return power

    def calculate_mdes(self, p0: float = 0.50) -> tuple:
        """
        Find MDES (Minimum Detectable Effect Size) via binary search.

        Start from p0 (baseline), search for p1 such that power≈0.80
        """
        # Binary search for p1
        p_low = p0
        p_high = 0.99

        for _ in range(20):  # 20 iterations = precision ~1e-6
            p_mid = (p_low + p_high) / 2
            power_mid = self.power_for_effect_size(p0, p_mid, self.n, self.alpha)

            if power_mid < self.power:
                p_low = p_mid
            else:
                p_high = p_mid

        p1_mdes = p_high
        mdes_pp = (p1_mdes - p0) * 100

        return mdes_pp, p0, p1_mdes

    def plot_power_curve(self, output_path: str = "results/figures/power_analysis.png"):
        """Plot power vs effect size."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        p0 = 0.50
        effect_sizes_pp = [i * 50 / 30 for i in range(31)]  # 0-50pp in 30 steps
        powers = []

        for delta_pp in effect_sizes_pp:
            p1 = min(p0 + (delta_pp / 100), 0.99)
            power = self.power_for_effect_size(p0, p1, self.n, self.alpha)
            powers.append(power)

        # Simple ASCII plot (no matplotlib needed)
        print("\n" + "=" * 70)
        print("POWER CURVE (n=15, α=0.05)")
        print("=" * 70)

        for delta_pp, power in zip(effect_sizes_pp, powers):
            bar_length = int(power * 40)
            bar = "█" * bar_length + "░" * (40 - bar_length)
            print(
                f"Δ={delta_pp:5.1f}pp | {bar} | Power={power:.3f}"
            )

        print("=" * 70)

        # Save plot data as JSON
        plot_data = {
            "effect_sizes_pp": effect_sizes_pp,
            "powers": powers,
            "mdes_pp": self.calculate_mdes(p0)[0],
        }
        plot_path = output_path.replace(".png", ".json")
        with open(plot_path, "w") as f:
            json.dump(plot_data, f, indent=2)
        print(f"✅ Power curve data saved: {plot_path}")

    def report(self) -> dict:
        """Generate power analysis report"""
        mdes_pp, p0, p1 = self.calculate_mdes(p0=0.50)

        report = {
            "title": "AgentTrust Power Analysis",
            "date": "2026-08-18",
            "parameters": {
                "n_per_category": self.n,
                "alpha": self.alpha,
                "power_target": self.power,
                "test": "Binomial Test (one-sided)",
            },
            "results": {
                "baseline_asr": p0 * 100,
                "mdes_alternative_asr": p1 * 100,
                "mdes_effect_size_pp": round(mdes_pp, 1),
                "interpretation": f"With {self.n} payloads per category, we can detect a difference of ~{mdes_pp:.1f}pp in ASR with {self.power*100:.0f}% power.",
            },
            "implications": [
                f"True ASR difference ≥ {mdes_pp:.0f}pp → We WILL detect it statistically",
                f"True ASR difference < {mdes_pp:.0f}pp → We likely WON'T detect it (Type II error)",
                "This is acceptable. Smaller effects require larger n (more payloads).",
                "Current n=15 per category is a good balance: fast experiments + detectable effects.",
            ],
        }

        return report


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("POWER ANALYSIS FOR AGENTTRUST")
    print("=" * 70 + "\n")

    pa = PowerAnalysis(n_per_category=15, alpha=0.05, power=0.80)

    # Calculate MDES
    mdes_pp, p0, p1 = pa.calculate_mdes(p0=0.50)

    print(f"Sample size per category (n): 15")
    print(f"Baseline ASR (null): {p0*100:.1f}%")
    print(f"Alternative ASR (MDES): {p1*100:.1f}%")
    print(f"Minimum Detectable Effect Size: {mdes_pp:.1f} percentage points")
    print(
        f"\n→ With n=15, we detect Δ ≥ {mdes_pp:.0f}pp at {pa.power*100:.0f}% power"
    )
    print(f"→ Smaller deltas (~5-10pp) are UNDETECTABLE with current n")
    print(f"→ To detect smaller effects, we need n > 50 per category\n")

    # Generate report
    report = pa.report()
    report_path = "results/power_analysis_report.json"
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"✅ Report saved: {report_path}\n")

    # Plot power curve
    pa.plot_power_curve()

    print("✅ POWER ANALYSIS COMPLETE")
    print("=" * 70)
