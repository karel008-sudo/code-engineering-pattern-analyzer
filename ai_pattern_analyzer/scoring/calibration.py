"""
scoring/calibration.py — Repo-level statistical calibration.

Instead of fixed global thresholds, derive per-repo percentile bands.
This makes the tool useful even when ALL files in a repo are AI-generated
(the distribution still gives relative ranking).

Outputs:
  - score distribution statistics
  - percentile-based tier assignment
  - repo-level AI-pattern summary
"""
from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from typing import List, Optional

from .model import FileAnalysis


@dataclass
class RepoStats:
    """Statistical summary for a scanned repository."""
    repo_name: str
    total_files: int
    production_files: int
    test_files: int

    # Likelihood distribution
    mean_likelihood: float
    median_likelihood: float
    std_dev: float
    p25: float      # 25th percentile
    p75: float      # 75th percentile
    p90: float      # 90th percentile

    # Classification counts
    ai_like_count: int
    human_like_count: int
    mixed_count: int
    uncertain_count: int

    # Top files
    top_ai_files: List[FileAnalysis] = field(default_factory=list)
    top_human_files: List[FileAnalysis] = field(default_factory=list)

    # Git signals (optional)
    git_signals: dict = field(default_factory=dict)

    @property
    def ai_like_pct(self) -> float:
        if self.production_files == 0:
            return 0.0
        return self.ai_like_count / self.production_files * 100

    @property
    def summary_label(self) -> str:
        """Repo-level qualitative label based on distribution."""
        if self.median_likelihood > 0.65:
            return "HIGH AI-like pattern density"
        if self.median_likelihood > 0.52:
            return "MODERATE AI-like patterns"
        if self.median_likelihood > 0.40:
            return "LOW / mixed AI patterns"
        return "Predominantly human-like patterns"


def _percentile(data: List[float], p: float) -> float:
    """Compute the p-th percentile (0–100) of a sorted list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


def calibrate_repo(
    repo_name: str,
    analyses: List[FileAnalysis],
    git_signals: Optional[dict] = None,
) -> RepoStats:
    """
    Compute statistical calibration for a repo's file analyses.
    Separates production and test files for statistics.
    """
    prod  = [a for a in analyses if a.kind == "production"]
    tests = [a for a in analyses if a.kind == "test"]

    all_likelihoods = [a.ai_likelihood for a in prod] if prod else [0.0]

    mean   = statistics.mean(all_likelihoods)
    median = statistics.median(all_likelihoods)
    std    = statistics.stdev(all_likelihoods) if len(all_likelihoods) > 1 else 0.0
    p25    = _percentile(all_likelihoods, 25)
    p75    = _percentile(all_likelihoods, 75)
    p90    = _percentile(all_likelihoods, 90)

    counts = {"AI-like": 0, "human-like": 0, "mixed": 0, "uncertain": 0}
    for a in prod:
        counts[a.classification] = counts.get(a.classification, 0) + 1

    top_ai = sorted(prod, key=lambda a: -a.ai_likelihood)[:10]
    top_hum = sorted(prod, key=lambda a: a.ai_likelihood)[:10]
    # Filter out files with very low confidence from top lists
    top_ai  = [a for a in top_ai  if a.confidence >= 0.45][:5]
    top_hum = [a for a in top_hum if a.confidence >= 0.45][:5]

    return RepoStats(
        repo_name=repo_name,
        total_files=len(analyses),
        production_files=len(prod),
        test_files=len(tests),
        mean_likelihood=round(mean, 4),
        median_likelihood=round(median, 4),
        std_dev=round(std, 4),
        p25=round(p25, 4),
        p75=round(p75, 4),
        p90=round(p90, 4),
        ai_like_count=counts.get("AI-like", 0),
        human_like_count=counts.get("human-like", 0),
        mixed_count=counts.get("mixed", 0),
        uncertain_count=counts.get("uncertain", 0),
        top_ai_files=top_ai,
        top_human_files=top_hum,
        git_signals=git_signals or {},
    )


def assign_percentile_tier(analysis: FileAnalysis, repo_stats: RepoStats) -> str:
    """
    Assign a percentile tier relative to the repo distribution.
    Useful for comparative statements: "top 10% most AI-like in this repo".
    """
    lh = analysis.ai_likelihood
    if lh >= repo_stats.p90: return "top-10%"
    if lh >= repo_stats.p75: return "top-25%"
    if lh >= repo_stats.median_likelihood: return "above-median"
    if lh >= repo_stats.p25: return "below-median"
    return "bottom-25%"
