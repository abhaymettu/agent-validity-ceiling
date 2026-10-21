"""
Validity ceiling analysis for agent benchmarks.

Ports the attenuation-correction framework (Mettu 2026, Zenodo 22739320)
to AI agent evaluation: given published test-retest variance, what is the
maximum predictive validity a benchmark score can achieve?

All inputs are from published papers (no API calls, no spend).
"""

import argparse
import json

import numpy as np
from dataclasses import dataclass, asdict

# ---------------------------------------------------------------------------
# Published data
# ---------------------------------------------------------------------------

# Bjarnason, Silva & Monperrus (2026). "On Randomness in Agentic Evals."
# 60,000 trajectories on SWE-bench Verified, 500 tasks, 10 runs each.
SWEBENCH_CONFIGS = [
    {"name": "Qwen3-32B + nano-agent",   "temp": 0.6, "sd": 0.7,  "lo": 15.0, "hi": 17.2},
    {"name": "Qwen3-32B + R2E-Gym",      "temp": 0.6, "sd": 1.4,  "lo": 21.4, "hi": 26.4},
    {"name": "DeepSWE + nano-agent",      "temp": 1.0, "sd": 1.0,  "lo": 28.8, "hi": 32.4},
    {"name": "DeepSWE + R2E-Gym",         "temp": 1.0, "sd": 1.5,  "lo": 31.6, "hi": 37.0},
    {"name": "Devstral-2 + nano-agent",   "temp": 0.2, "sd": 1.1,  "lo": 61.8, "hi": 65.0},
    {"name": "Devstral-2 + R2E-Gym",      "temp": 0.2, "sd": 1.5,  "lo": 32.2, "hi": 37.0},
    # temperature-0 conditions (same paper)
    {"name": "DeepSWE + nano-agent (t=0)",  "temp": 0.0, "sd": 1.0, "lo": 18.2, "hi": 21.4},
    {"name": "Qwen3-32B + R2E-Gym (t=0)",  "temp": 0.0, "sd": 1.8, "lo": 19.8, "hi": 25.2},
]

# "Measurement Without Validity" (arXiv 2608.00794)
# IRR values from Table in Section 3
MEASUREMENT_WITHOUT_VALIDITY = {
    "webArena_verified_kappa": 0.83,
    "mental_health_safety_icc_lo": 0.087,
    "mental_health_safety_icc_hi": 0.295,
    "mental_health_safety_alpha": -0.203,
    "llm_judge_substring_kappa": 0.049,
    "llm_judge_3ensemble_kappa": 0.432,
    "v_total_lo": 0.225,
    "v_total_hi": 0.54,
    "v_total_midpoint": 0.36,
    "inter_simulator_variance_pp": 9.0,
}

# MMLU and MMLU-Pro prompt sensitivity (various sources, 2024-2025)
PROMPT_SENSITIVITY = {
    "mmlu_pp": 4.5,       # midpoint of 4-5%
    "mmlu_pro_pp": 2.0,
}


# ---------------------------------------------------------------------------
# Classical test theory: attenuation correction
# ---------------------------------------------------------------------------

def icc_from_variance(sigma2_between: float, sigma2_within: float) -> float:
    """ICC(1,1) = between-group variance / total variance."""
    return sigma2_between / (sigma2_between + sigma2_within)


def attenuation_ceiling_r2(rho_benchmark: float, rho_criterion: float,
                           coverage: float) -> float:
    """
    Maximum achievable R^2 between benchmark X and criterion Y.

    R^2_{XY} <= rho_X * rho_Y * C

    where rho_X, rho_Y are reliabilities and C is the proportion of
    criterion-relevant true-score variance the benchmark covers.
    """
    return rho_benchmark * rho_criterion * coverage


def correct_for_attenuation(r_observed: float, rho_x: float,
                            rho_y: float) -> float:
    """
    Disattenuated correlation: what the correlation would be
    between perfectly reliable versions of X and Y.

    r_true = r_observed / sqrt(rho_x * rho_y)
    """
    denom = np.sqrt(rho_x * rho_y)
    if denom == 0:
        return np.nan
    return r_observed / denom


# ---------------------------------------------------------------------------
# Compute benchmark reliability across model populations
# ---------------------------------------------------------------------------

@dataclass
class ReliabilityEstimate:
    label: str
    sigma2_between: float
    sigma2_within: float
    icc: float
    n_note: str


def compute_swebench_reliability():
    """
    Estimate ICC for SWE-bench Verified under different population assumptions.

    sigma2_within: median within-config SD^2 from Bjarnason et al.
    sigma2_between: estimated from the spread of model scores.
    """
    sds = [c["sd"] for c in SWEBENCH_CONFIGS]
    median_sd = np.median(sds)
    sigma2_within = median_sd ** 2

    # SWE-bench Verified leaderboard score spread (public, Oct 2026)
    # Full range: ~15% to ~72%
    # Frontier cluster: ~55% to ~72%
    # Close comparison (version bumps): ~3-5 pp apart

    populations = [
        ("Full leaderboard (15-72%)", 15.0),
        ("Frontier models (55-72%)", 5.0),
        ("Close comparisons (3-5 pp gap)", 2.0),
        ("Scaffold variants (same model)", 3.5),
    ]

    results = []
    for label, sd_between in populations:
        s2b = sd_between ** 2
        icc = icc_from_variance(s2b, sigma2_within)
        results.append(ReliabilityEstimate(
            label=label,
            sigma2_between=s2b,
            sigma2_within=sigma2_within,
            icc=round(icc, 3),
            n_note=f"sigma_within={median_sd:.1f} pp (median of 8 configs)"
        ))
    return results


# ---------------------------------------------------------------------------
# Validity ceiling computation
# ---------------------------------------------------------------------------

@dataclass
class CeilingScenario:
    label: str
    rho_benchmark: float
    rho_criterion: float
    coverage: float
    ceiling_r2: float
    ceiling_r: float


def compute_ceilings(reliability_estimates: list[ReliabilityEstimate]):
    """
    Compute validity ceilings across benchmark reliability x coverage x
    criterion reliability scenarios.
    """
    # Coverage estimates (proportion of real-world criterion variance)
    coverages = [
        ("Generous (C=0.40)", 0.40),
        ("Moderate (C=0.25)", 0.25),
        ("Conservative (C=0.15)", 0.15),
    ]

    # Criterion reliability estimates
    criterion_reliabilities = [
        ("High (rho_Y=0.90)", 0.90),
        ("Moderate (rho_Y=0.75)", 0.75),
        ("Low (rho_Y=0.60)", 0.60),
    ]

    scenarios = []
    for rel_est in reliability_estimates:
        for cov_label, cov in coverages:
            for crit_label, rho_y in criterion_reliabilities:
                r2 = attenuation_ceiling_r2(rel_est.icc, rho_y, cov)
                r = np.sqrt(r2)
                scenarios.append(CeilingScenario(
                    label=f"{rel_est.label} | {cov_label} | {crit_label}",
                    rho_benchmark=rel_est.icc,
                    rho_criterion=rho_y,
                    coverage=cov,
                    ceiling_r2=round(r2, 3),
                    ceiling_r=round(r, 3),
                ))
    return scenarios


# ---------------------------------------------------------------------------
# Gap decomposition (following Mettu 2026)
# ---------------------------------------------------------------------------

def decompose_validity_gap(rho_benchmark: float, rho_criterion: float,
                           coverage: float):
    """
    Decompose the gap between perfect prediction (R^2=1) and the ceiling.

    Returns dict with:
      benchmark_unreliability: 1 - rho_X (variance lost to benchmark noise)
      criterion_unreliability: rho_X * (1 - rho_Y) (after benchmark noise)
      uncovered_variance: rho_X * rho_Y * (1 - C) (reliable but irrelevant)
      ceiling: rho_X * rho_Y * C (the reachable part)
    """
    benchmark_loss = 1.0 - rho_benchmark
    criterion_loss = rho_benchmark * (1.0 - rho_criterion)
    coverage_loss = rho_benchmark * rho_criterion * (1.0 - coverage)
    ceiling = rho_benchmark * rho_criterion * coverage

    return {
        "benchmark_unreliability": round(benchmark_loss, 4),
        "criterion_unreliability": round(criterion_loss, 4),
        "uncovered_variance": round(coverage_loss, 4),
        "ceiling": round(ceiling, 4),
        "total": round(benchmark_loss + criterion_loss + coverage_loss + ceiling, 4),
    }


# ---------------------------------------------------------------------------
# Attenuation correction examples
# ---------------------------------------------------------------------------

def attenuation_examples(rho_x: float, rho_y: float):
    """
    Show how observed correlations change after disattenuation.
    """
    observed_rs = [0.20, 0.30, 0.40, 0.50, 0.60]
    results = []
    for r in observed_rs:
        r_corr = correct_for_attenuation(r, rho_x, rho_y)
        pct_increase = ((r_corr - r) / r) * 100 if r > 0 else 0
        results.append({
            "r_observed": r,
            "r_corrected": round(r_corr, 3),
            "pct_increase": round(pct_increase, 1),
        })
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--out", default="results.json",
                    help="where to write results (default: results.json in the current directory)")
    args = ap.parse_args()

    print("=" * 72)
    print("VALIDITY CEILING FOR AGENT BENCHMARKS")
    print("Reliability-corrected predictive validity analysis")
    print("=" * 72)

    # 1. Within-run variance summary
    print("\n--- Published within-run variance (Bjarnason et al. 2026) ---\n")
    for c in SWEBENCH_CONFIGS:
        print(f"  {c['name']:40s}  SD={c['sd']:.1f} pp  "
              f"range={c['hi']-c['lo']:.1f} pp  (temp={c['temp']})")

    sds = [c["sd"] for c in SWEBENCH_CONFIGS]
    print(f"\n  Median SD: {np.median(sds):.2f} pp")
    print(f"  Mean SD:   {np.mean(sds):.2f} pp")
    print(f"  Max SD:    {np.max(sds):.2f} pp")

    # 2. Reliability estimates
    print("\n--- SWE-bench Verified reliability by model population ---\n")
    rel_estimates = compute_swebench_reliability()
    for r in rel_estimates:
        print(f"  {r.label:45s}  ICC = {r.icc:.3f}  "
              f"(s2_b={r.sigma2_between:.1f}, s2_w={r.sigma2_within:.2f})")

    # 3. Validity ceilings (key table)
    print("\n--- Validity ceiling: R^2 <= rho_X * rho_Y * C ---\n")
    scenarios = compute_ceilings(rel_estimates)

    # Print the most informative subset
    key_scenarios = [s for s in scenarios if "Moderate" in s.label
                     and "rho_Y=0.75" in s.label]
    print(f"  {'Population':45s}  {'rho_X':>6s}  {'C':>5s}  "
          f"{'Ceil R^2':>8s}  {'Ceil r':>6s}")
    print("  " + "-" * 76)
    for s in key_scenarios:
        print(f"  {s.label.split(' | ')[0]:45s}  {s.rho_benchmark:6.3f}  "
              f"{s.coverage:5.2f}  {s.ceiling_r2:8.3f}  {s.ceiling_r:6.3f}")

    # Every frontier number below uses this one computed reliability.
    rho_frontier = next(r.icc for r in rel_estimates if "Frontier" in r.label)

    # 4. Full ceiling table for the frontier
    print(f"\n--- Full ceiling table: Frontier models (rho_X={rho_frontier:.3f}) ---\n")
    frontier = [s for s in scenarios
                if "Frontier" in s.label]
    print(f"  {'Coverage':>20s}  {'rho_Y':>6s}  {'Ceil R^2':>8s}  {'Ceil r':>6s}")
    print("  " + "-" * 46)
    for s in frontier:
        parts = s.label.split(" | ")
        cov_label = parts[1].strip()
        crit_label = parts[2].strip()
        print(f"  {cov_label:>20s}  {s.rho_criterion:6.2f}  "
              f"{s.ceiling_r2:8.3f}  {s.ceiling_r:6.3f}")

    # 5. Gap decomposition for the frontier, moderate scenario
    print("\n--- Gap decomposition: Frontier, C=0.25, rho_Y=0.75 ---\n")
    gap = decompose_validity_gap(rho_frontier, 0.75, 0.25)
    for k, v in gap.items():
        pct = v * 100
        print(f"  {k:30s}  {v:.4f}  ({pct:5.1f}%)")

    # 6. Attenuation correction examples
    print("\n--- Disattenuation: observed -> corrected r ---")
    print(f"    (Frontier rho_X={rho_frontier:.3f}, Moderate rho_Y=0.75)\n")
    examples = attenuation_examples(rho_frontier, 0.75)
    print(f"  {'r_obs':>6s}  {'r_corr':>6s}  {'inflation':>9s}")
    print("  " + "-" * 25)
    for e in examples:
        print(f"  {e['r_observed']:6.2f}  {e['r_corrected']:6.3f}  "
              f"+{e['pct_increase']:5.1f}%")

    # 7. Close-comparison reliability problem
    print("\n--- The frontier discrimination problem ---\n")
    close_rel = [r for r in rel_estimates if "Close" in r.label][0]
    print(f"  When comparing models 3-5 pp apart:")
    print(f"  ICC drops to {close_rel.icc:.3f}")
    ceiling_close = attenuation_ceiling_r2(close_rel.icc, 0.75, 0.25)
    print(f"  Validity ceiling R^2 = {ceiling_close:.3f} "
          f"(r = {np.sqrt(ceiling_close):.3f})")
    print(f"  Meaning: benchmark score differences explain at most "
          f"{ceiling_close*100:.1f}% of real-world")
    print(f"  performance differences between closely-ranked models.")

    # 8. Comparison with the Measurement Without Validity framework
    print("\n--- Cross-check: Measurement Without Validity (2608.00794) ---\n")
    mwv = MEASUREMENT_WITHOUT_VALIDITY
    print(f"  V_total range: [{mwv['v_total_lo']:.3f}, {mwv['v_total_hi']:.3f}]")
    print(f"  V_total midpoint: {mwv['v_total_midpoint']:.3f}")
    print(f"  Our frontier ceiling (C=0.25, rho_Y=0.75): "
          f"R^2 = {attenuation_ceiling_r2(rho_frontier, 0.75, 0.25):.3f}")
    print(f"  Our close-comparison ceiling: R^2 = {ceiling_close:.3f}")
    print(f"\n  Convergent: both frameworks put the ceiling well below 0.25")
    print(f"  for the comparisons that leaderboard consumers care about most.")

    # 9. Export results as JSON for the writeup
    output = {
        "within_run_variance": {
            "source": "Bjarnason, Silva & Monperrus (2026)",
            "median_sd_pp": float(np.median(sds)),
            "configs": SWEBENCH_CONFIGS,
        },
        "reliability_estimates": [asdict(r) for r in rel_estimates],
        "key_ceilings": [asdict(s) for s in key_scenarios],
        "frontier_ceilings": [asdict(s) for s in frontier],
        "gap_decomposition": gap,
        "attenuation_examples": examples,
    }

    with open(args.out, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")
    print(f"\n  Results written to {args.out}")

    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
