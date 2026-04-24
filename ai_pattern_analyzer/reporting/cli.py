"""
reporting/cli.py — Terminal output: tables, histograms, summaries.
"""
from __future__ import annotations
import shutil
from pathlib import Path
from typing import List, Optional

from ..scoring.calibration import RepoStats
from ..scoring.model import FileAnalysis


DISCLAIMER = """
⚠  IMPORTANT: This tool detects CODE GENERATION PATTERNS — it does NOT prove authorship.
   Results are probabilistic signals based on style heuristics and statistical analysis.
   High AI-likelihood scores reflect code style patterns, not verified code origin.
   Do NOT use these results as evidence of policy violations or personnel decisions.
"""

_TERM_WIDTH = min(shutil.get_terminal_size(fallback=(100, 40)).columns, 120)


def _bar(value: float, width: int = 20, char_ai: str = "█", char_hum: str = "░") -> str:
    filled = int(value * width)
    return char_ai * filled + char_hum * max(0, width - filled)


def _likelihood_color(lh: float) -> str:
    """ANSI color based on likelihood — green=human, red=AI, yellow=mixed."""
    if lh >= 0.65: return "\033[91m"   # red
    if lh >= 0.50: return "\033[93m"   # yellow
    return "\033[92m"                  # green


_RESET = "\033[0m"


def print_disclaimer() -> None:
    print(DISCLAIMER)


def print_repo_summary(stats: RepoStats, use_color: bool = True) -> None:
    w = _TERM_WIDTH
    print()
    print("═" * w)
    print(f"  REPO: {stats.repo_name}")
    print(f"  {stats.summary_label}")
    print("═" * w)

    # Distribution bar
    bar_w = 40
    median_filled = int(stats.median_likelihood * bar_w)
    bar = "▓" * median_filled + "░" * (bar_w - median_filled)
    print(f"  Median AI-likelihood: {stats.median_likelihood:.3f}  [{bar}]")
    print(f"  Mean: {stats.mean_likelihood:.3f}  StdDev: {stats.std_dev:.3f}  "
          f"P25: {stats.p25:.3f}  P75: {stats.p75:.3f}  P90: {stats.p90:.3f}")
    print()

    # Classification breakdown
    total = max(stats.production_files, 1)
    print(f"  Files: {stats.production_files} production | {stats.test_files} test")
    for label, count in [
        ("AI-like",    stats.ai_like_count),
        ("human-like", stats.human_like_count),
        ("mixed",      stats.mixed_count),
        ("uncertain",  stats.uncertain_count),
    ]:
        pct = count / total * 100
        bar = _bar(pct / 100, width=15)
        print(f"    {label:<12} {count:>5}  ({pct:5.1f}%)  [{bar}]")

    # Score histogram
    print()
    print("  Likelihood histogram (production files):")
    _print_histogram(stats)

    # Git signals
    if stats.git_signals:
        print()
        print("  Git pattern signals:")
        for k, v in stats.git_signals.items():
            bar = _bar(v, width=12)
            label = f"{v:.2f}"
            print(f"    {k:<28} {label}  [{bar}]")

    # Top AI-like files
    if stats.top_ai_files:
        print()
        print("  Top AI-like files (highest likelihood):")
        print(f"  {'Likelihood':>10}  {'Conf':>5}  {'Lang':<8}  {'Classification':<12}  File")
        print(f"  {'─'*10}  {'─'*5}  {'─'*8}  {'─'*12}  {'─'*40}")
        for a in stats.top_ai_files:
            fname = Path(a.path).name
            pth   = Path(a.path)
            short = "/".join(pth.parts[-2:]) if len(pth.parts) >= 2 else fname
            color = _likelihood_color(a.ai_likelihood) if use_color else ""
            reset = _RESET if use_color else ""
            print(f"  {color}{a.ai_likelihood:>10.3f}{reset}  {a.confidence:>5.2f}"
                  f"  {a.language:<8}  {a.classification:<12}  {short[-45:]}")

    # Top human-like files
    if stats.top_human_files:
        print()
        print("  Most human-like files (lowest likelihood):")
        for a in stats.top_human_files:
            pth = Path(a.path)
            short = "/".join(pth.parts[-2:]) if len(pth.parts) >= 2 else pth.name
            print(f"    {a.ai_likelihood:.3f}  {a.language:<10}  {short[-50:]}")

    print("═" * w)


def _print_histogram(stats: RepoStats) -> None:
    """ASCII histogram of likelihood distribution."""
    # We don't have individual values in RepoStats — approximate from percentiles
    # Use a simple bucket representation from the percentile data
    buckets = {
        "0.0–0.2": 0, "0.2–0.4": 0, "0.4–0.6": 0, "0.6–0.8": 0, "0.8–1.0": 0,
    }
    # Estimate distribution shape from percentiles
    def _est(val: float) -> str:
        if val < 0.20: return "0.0–0.2"
        if val < 0.40: return "0.2–0.4"
        if val < 0.60: return "0.4–0.6"
        if val < 0.80: return "0.6–0.8"
        return "0.8–1.0"

    # We only have p25, median, p75, p90 — show them as markers
    markers = {
        stats.p25:               "p25",
        stats.median_likelihood: "median",
        stats.p75:               "p75",
        stats.p90:               "p90",
    }
    bar_w = 50
    print(f"  {'0.0':<5}{'':>{bar_w - 7}}{'1.0':>4}")
    bar = list("░" * bar_w)
    for val, label in markers.items():
        pos = min(int(val * bar_w), bar_w - 1)
        bar[pos] = "│"
    print(f"  [{''.join(bar)}]")
    marker_line = [" "] * bar_w
    for val, label in markers.items():
        pos = min(int(val * bar_w), bar_w - 1)
        marker_line[pos] = "^"
    labels = " ".join(f"{l}={v:.2f}" for v, l in sorted(markers.items()))
    print(f"  {''.join(marker_line)}")
    print(f"  {labels}")


def print_multi_repo_table(all_stats: List[RepoStats]) -> None:
    """Summary table across multiple repos."""
    print()
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║          CODE GENERATION PATTERN ANALYZER v3.0 — RESULTS               ║")
    print("╠══════════════════════════════════════════════════════════════════════════╣")
    print(f"║  {'Repo':<30}  {'Median':>7}  {'P90':>6}  {'AI-like%':>9}  {'Files':>6}  {'Pattern':<18}  ║")
    print(f"║  {'─'*30}  {'─'*7}  {'─'*6}  {'─'*9}  {'─'*6}  {'─'*18}  ║")
    for s in sorted(all_stats, key=lambda x: -x.median_likelihood):
        label = s.summary_label[:18]
        bar   = _bar(s.median_likelihood, width=8)
        print(f"║  {s.repo_name[:30]:<30}  {s.median_likelihood:>7.3f}  "
              f"{s.p90:>6.3f}  {s.ai_like_pct:>8.1f}%  "
              f"{s.production_files:>6}  {label:<18}  ║")
    print("╠══════════════════════════════════════════════════════════════════════════╣")
    total_files = sum(s.production_files for s in all_stats)
    total_ai    = sum(s.ai_like_count for s in all_stats)
    overall_pct = total_ai / max(total_files, 1) * 100
    print(f"║  {'TOTAL':<30}  {'':>7}  {'':>6}  {overall_pct:>8.1f}%  {total_files:>6}  {'':18}  ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
