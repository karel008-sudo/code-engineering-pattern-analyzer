"""
reporting/cli.py — Terminal output: tables, histograms, summaries.

v4.0 additions:
  - Shows adjusted_score alongside ai_likelihood
  - Shows category and risk_score
  - Shows module heatmap
  - Shows high-risk files separately
  - Updated disclaimer with careful wording
  - Shows data quality and exclusions
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

from ..scoring.calibration import RepoStats
from ..scoring.model import FileAnalysis
from ..config import ANALYZER_VERSION, SCORING_MODEL_VERSION


DISCLAIMER = """
┌─────────────────────────────────────────────────────────────────────────────┐
│  ⚠  AI PATTERN ANALYZER — IMPORTANT NOTICE                                 │
│                                                                             │
│  This tool detects AI-LIKE CODE PATTERNS using heuristics.                 │
│  It does NOT prove AI authorship, does NOT identify code origin,            │
│  and MUST NOT be used for personnel decisions or compliance claims.         │
│  Results are probabilistic pattern signals — directional indicators only.   │
│                                                                             │
│  High scores may reflect: senior clean code, strict formatters, DTOs,      │
│  framework boilerplate, generated clients, or heavy refactoring.            │
└─────────────────────────────────────────────────────────────────────────────┘
"""

_TERM_WIDTH = min(shutil.get_terminal_size(fallback=(100, 40)).columns, 120)


def _bar(value: float, width: int = 20, char_ai: str = "█", char_hum: str = "░") -> str:
    filled = int(value * width)
    return char_ai * filled + char_hum * max(0, width - filled)


def _likelihood_color(lh: float) -> str:
    if lh >= 0.65: return "\033[91m"   # red
    if lh >= 0.45: return "\033[93m"   # yellow
    return "\033[92m"                  # green


_RESET = "\033[0m"


def print_disclaimer() -> None:
    print(DISCLAIMER)


def print_repo_summary(stats: RepoStats, use_color: bool = True) -> None:
    w = _TERM_WIDTH
    print()
    print("═" * w)
    print(f"  REPO: {stats.repo_name}  |  {stats.summary_label}")
    print(f"  Analyzer: {ANALYZER_VERSION}  |  Scoring model: {SCORING_MODEL_VERSION}")
    print("═" * w)

    # v5.0: AI-Adoption Pattern Index (fixed naming, not "AI-generated files %")
    bar_w = 40
    kpi_filled = int(stats.kpi_score * bar_w)
    kpi_band = "LOW" if stats.kpi_score < 0.26 else "MODERATE" if stats.kpi_score < 0.51 else "ELEVATED" if stats.kpi_score < 0.76 else "HIGH"
    bar = "▓" * kpi_filled + "░" * (bar_w - kpi_filled)
    print(f"  AI-Adoption Pattern Index: {stats.kpi_score * 100:5.1f}% [{kpi_band}]  [{bar}]")
    print(f"  ⚠ This is NOT a percentage of AI-generated files.")
    print(f"    It is a directional KPI based on code pattern signals.")
    print()

    # Raw likelihood
    lh_filled = int(stats.median_likelihood * bar_w)
    lh_bar = "█" * lh_filled + "░" * (bar_w - lh_filled)
    print(f"  Raw likelihood (median):  {stats.median_likelihood * 100:5.1f}%  [{lh_bar}]")
    print(f"  Mean: {stats.mean_likelihood:.3f}  StdDev: {stats.std_dev:.3f}  "
          f"P25: {stats.p25:.3f}  P75: {stats.p75:.3f}  P90: {stats.p90:.3f}")
    print(f"  Data quality: {stats.data_quality_score:.0%}"
          f"  |  Generated excluded: {stats.exclusions.get('generated_excluded', 0)}"
          f"  |  KPI-eligible: {stats.exclusions.get('kpi_eligible', 0)}")
    print()

    # v5.0: AI Origin Estimate
    if stats.origin_estimate:
        oe = stats.origin_estimate
        print(f"  ── AI Origin Pattern Estimate ──────────────────────────────────────")
        print(f"  ⚠ Pattern estimates only — NOT proof of actual authorship")
        print(f"  Fully AI-like pattern signals: {oe.fully_ai_generated_pct:5.1f}%"
              f"  confidence: {oe.confidence}")
        print(f"  AI-assisted pattern signals:   {oe.ai_assisted_pct:5.1f}%")
        print(f"  Human-pattern signals:         {oe.human_authored_pct:5.1f}%")
        total_check = oe.fully_ai_generated_pct + oe.ai_assisted_pct + oe.human_authored_pct
        print(f"  (Sum: {total_check:.1f}%  |  Generated/vendor files excluded)")
        print()

    # File counts
    print(f"  Files: {stats.production_files} production | "
          f"{stats.test_files} test | "
          f"{stats.generated_files} generated (excluded from KPI)")

    # Classification breakdown
    total = max(stats.production_files, 1)
    print()
    print("  Classification (production files):")
    for label, count in [
        ("AI-like",    stats.ai_like_count),
        ("human-like", stats.human_like_count),
        ("mixed",      stats.mixed_count),
        ("uncertain",  stats.uncertain_count),
    ]:
        pct = count / total * 100
        bar = _bar(pct / 100, width=15)
        print(f"    {label:<12} {count:>5}  ({pct:5.1f}%)  [{bar}]")

    # Category breakdown
    if stats.category_summaries:
        print()
        print("  Category breakdown:")
        print(f"  {'Category':<22}  {'Files':>5}  {'Adj.Score':>9}  {'Confidence':>10}")
        print(f"  {'─'*22}  {'─'*5}  {'─'*9}  {'─'*10}")
        for cat in sorted(stats.category_summaries, key=lambda c: -c.mean_adjusted):
            print(f"  {cat.category:<22}  {cat.file_count:>5}  "
                  f"{cat.mean_adjusted:>8.1%}  {cat.mean_confidence:>9.1%}")

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
            print(f"    {k:<28} {v:.2f}  [{bar}]")

    # Module heatmap (top 5)
    if stats.module_summaries:
        print()
        print("  Module heatmap (top modules by adjusted score):")
        print(f"  {'Module':<35}  {'Files':>5}  {'Adj.Score':>9}  {'Risk':>6}")
        print(f"  {'─'*35}  {'─'*5}  {'─'*9}  {'─'*6}")
        for mod in stats.module_summaries[:7]:
            color = _likelihood_color(mod.mean_adjusted) if use_color else ""
            reset = _RESET if use_color else ""
            print(f"  {color}{mod.module_path[:35]:<35}{reset}  "
                  f"{mod.file_count:>5}  "
                  f"{mod.mean_adjusted:>8.1%}  "
                  f"{mod.mean_risk:>5.1%}")

    # High-risk files
    if stats.top_risk_files:
        print()
        print("  High-risk files (by risk_score):")
        print(f"  {'File':<40}  {'Category':<18}  {'Adj':>6}  {'Risk':>6}  {'Conf':>5}")
        print(f"  {'─'*40}  {'─'*18}  {'─'*6}  {'─'*6}  {'─'*5}")
        for a in stats.top_risk_files[:7]:
            pth  = Path(a.path)
            short = "/".join(pth.parts[-2:]) if len(pth.parts) >= 2 else pth.name
            color = _likelihood_color(a.risk_score) if use_color else ""
            reset = _RESET if use_color else ""
            print(f"  {color}{short[:40]:<40}{reset}  "
                  f"{a.category.value[:18]:<18}  "
                  f"{a.adjusted_score:>5.1%}  "
                  f"{a.risk_score:>5.1%}  "
                  f"{a.confidence:>5.2f}")

    # Top high-signal files (by raw score, for context)
    if stats.top_ai_files:
        print()
        print("  Top high-signal files (elevated AI-like pattern score — not proven AI origin):")
        print(f"  {'Likelihood':>10}  {'Adj':>5}  {'Conf':>5}  {'Lang':<8}  {'Category':<18}  File")
        print(f"  {'─'*10}  {'─'*5}  {'─'*5}  {'─'*8}  {'─'*18}  {'─'*35}")
        for a in stats.top_ai_files:
            pth  = Path(a.path)
            short = "/".join(pth.parts[-2:]) if len(pth.parts) >= 2 else pth.name
            color = _likelihood_color(a.ai_likelihood) if use_color else ""
            reset = _RESET if use_color else ""
            print(f"  {color}{a.ai_likelihood:>10.3f}{reset}  "
                  f"{a.adjusted_score:>5.3f}  "
                  f"{a.confidence:>5.2f}  "
                  f"{a.language:<8}  "
                  f"{a.category.value[:18]:<18}  "
                  f"{short[-35:]}")

    print("═" * w)


def _print_histogram(stats: RepoStats) -> None:
    """ASCII histogram of likelihood distribution using percentile markers."""
    markers = {
        stats.p25:               "p25",
        stats.median_likelihood: "med",
        stats.p75:               "p75",
        stats.p90:               "p90",
    }
    bar_w = 50
    print(f"  {'0.0':<5}{'':>{bar_w - 7}}{'1.0':>4}")
    bar = list("░" * bar_w)
    for val in markers:
        pos = min(int(val * bar_w), bar_w - 1)
        bar[pos] = "│"
    print(f"  [{''.join(bar)}]")
    marker_line = [" "] * bar_w
    for val in markers:
        pos = min(int(val * bar_w), bar_w - 1)
        marker_line[pos] = "^"
    labels = "  ".join(f"{l}={v:.2f}" for v, l in sorted(markers.items()))
    print(f"  {''.join(marker_line)}")
    print(f"  {labels}")


def print_multi_repo_table(all_stats: List[RepoStats]) -> None:
    """Summary table across multiple repos with v4.0 fields."""
    w = 90
    print()
    print("╔" + "═" * (w - 2) + "╗")
    print(f"║  CODE ENGINEERING PATTERN ANALYZER v{ANALYZER_VERSION} — RESULTS"
          + " " * (w - 52 - len(ANALYZER_VERSION)) + "║")
    print("╠" + "═" * (w - 2) + "╣")
    header = (f"║  {'Repo':<25}  {'KPI%':>5}  {'Sig>Thr%':>8}  "
              f"{'Adj':>5}  {'Risk':>5}  {'Files':>5}  {'Pattern label':<20}  ║")
    # Note: 'Sig>Thr%' = % of files exceeding pattern-signal threshold
    #       This is NOT "% of files written by AI"
    print(header)
    print("╠" + "═" * (w - 2) + "╣")
    for s in sorted(all_stats, key=lambda x: -x.kpi_score):
        label = s.summary_label[:20]
        print(
            f"║  {s.repo_name[:25]:<25}  {s.kpi_score:>4.1%}  "
            f"{s.ai_like_pct:>7.1f}%  "
            f"{s.mean_adjusted:>5.3f}  "
            f"{s.mean_risk:>5.3f}  "
            f"{s.production_files:>5}  "
            f"{label:<20}  ║"
        )
    print("╠" + "═" * (w - 2) + "╣")
    total_files = sum(s.production_files for s in all_stats)
    total_ai    = sum(s.ai_like_count for s in all_stats)
    overall_pct = total_ai / max(total_files, 1) * 100
    avg_kpi     = sum(s.kpi_score for s in all_stats) / max(len(all_stats), 1)
    print(f"║  {'TOTAL / AVERAGE':<25}  {avg_kpi:>4.1%}  {overall_pct:>7.1f}%  "
          f"{'':>5}  {'':>5}  {total_files:>5}  {'':20}  ║")
    print("╠" + "═" * (w - 2) + "╣")
    print(f"║  ⚠ AI-Adoption Pattern Index is NOT '% of files written by AI'.{' '*(w-69)}║")
    print(f"║    It is a directional code-pattern signal — see README for interpretation.{' '*(w-79)}║")
    print("╚" + "═" * (w - 2) + "╝")


def print_repo_origin_estimate(stats: RepoStats, use_color: bool = True) -> None:
    """Print a detailed AI Origin Estimate for a repository (--explain-repo mode)."""
    w = _TERM_WIDTH
    print()
    print("═" * w)
    print(f"  AI Origin Estimate — {stats.repo_name}")
    print(f"  ⚠ Heuristic estimate, NOT forensic proof of AI authorship")
    print("═" * w)

    if not stats.origin_estimate:
        print("  No origin estimate available (insufficient data or no files analyzed).")
        print("═" * w)
        return

    oe = stats.origin_estimate

    print(f"""
  AI Origin Pattern Estimate:
  ─────────────────────────────────────────────────────────────────
  Fully AI-like pattern signals:   {oe.fully_ai_generated_pct:5.1f}%    confidence: {oe.confidence}
    (patterns consistent with full AI/scaffold generation — not proven)
  AI-assisted pattern signals:     {oe.ai_assisted_pct:5.1f}%    confidence: {oe.confidence}
    (patterns consistent with AI-assisted editing — not proven)
  Human-pattern signals:           {oe.human_authored_pct:5.1f}%    confidence: {oe.confidence}
    (patterns consistent with human-authored code — not proven)
  ─────────────────────────────────────────────────────────────────
  Sum: {oe.fully_ai_generated_pct + oe.ai_assisted_pct + oe.human_authored_pct:.1f}%
  ⚠ Generated/vendor files excluded. Pattern signals only — not authorship proof.
""")

    # Confidence intervals
    if oe.intervals:
        print("  Confidence intervals:")
        for key, interval in oe.intervals.items():
            if hasattr(interval, 'low'):
                print(f"    {key:<25} {interval.low:.1f}% – {interval.high:.1f}%")
    print()

    # Drivers
    if oe.drivers:
        print("  Key drivers:")
        for d in oe.drivers:
            print(f"    • {d}")
    print()

    # Uncertainty
    if oe.uncertainty_reasons:
        print("  Uncertainty reasons:")
        for r in oe.uncertainty_reasons:
            print(f"    ⚠ {r}")
    print()

    # Interpretation guidance
    print("  Interpretation:")
    print(f"  AI-Adoption Pattern Index: {stats.kpi_score*100:.1f}%")
    if stats.kpi_score < 0.26:
        print("  → Low AI-like signal density. Consistent with established codebases")
        print("    with strong human-authorship signals.")
    elif stats.kpi_score < 0.51:
        print("  → Moderate AI-like patterns. May reflect clean code, formatters,")
        print("    framework conventions, or moderate AI-assisted development.")
    elif stats.kpi_score < 0.76:
        print("  → Elevated AI-like patterns. Warrants contextual review.")
    else:
        print("  → High AI-like pattern density. Strong candidate for review.")
        print("    Check for generated clients, DTOs, or scaffold generation.")

    print()
    print("  Caveats:")
    for c in oe.caveats:
        print(f"    • {c}")
    print("═" * w)
