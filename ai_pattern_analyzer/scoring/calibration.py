"""
scoring/calibration.py — Repo-level statistical calibration and module aggregation.

v4.0 additions:
  - Module-level aggregation by package/folder
  - Category-level breakdown (production, dto, test, generated, config)
  - Language-level breakdown
  - Data quality score (confidence in analysis completeness)
  - Generated code exclusion transparency

Design:
  - Repository and module scores weight by confidence, semantic LOC,
    and file category (production_logic weighted more than DTOs)
  - KPI score excludes generated, vendor, and example files
  - All statistics use production_logic files by default for KPI

⚠ Per-repo statistics are approximate. Calibration is heuristic.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model import FileAnalysis
from ..domain import FileCategory


# ── Module summary ─────────────────────────────────────────────────────────────

@dataclass
class ModuleSummary:
    """Statistical summary for a module (package/folder)."""
    module_path: str
    file_count: int
    mean_adjusted: float
    median_adjusted: float
    mean_risk: float
    ai_like_count: int
    languages: List[str]
    top_files: List[str] = field(default_factory=list)

    @property
    def ai_like_pct(self) -> float:
        return self.ai_like_count / max(self.file_count, 1) * 100

    def as_dict(self) -> dict:
        return {
            "module_path":    self.module_path,
            "file_count":     self.file_count,
            "mean_adjusted":  round(self.mean_adjusted, 4),
            "median_adjusted": round(self.median_adjusted, 4),
            "mean_risk":      round(self.mean_risk, 4),
            "ai_like_pct":    round(self.ai_like_pct, 2),
            "languages":      self.languages,
            "top_files":      self.top_files[:5],
        }


# ── Category summary ───────────────────────────────────────────────────────────

@dataclass
class CategorySummary:
    """Statistics for a specific file category within a repo."""
    category: str
    file_count: int
    mean_adjusted: float
    mean_confidence: float

    def as_dict(self) -> dict:
        return {
            "category":       self.category,
            "file_count":     self.file_count,
            "mean_adjusted":  round(self.mean_adjusted, 4),
            "mean_confidence": round(self.mean_confidence, 4),
        }


# ── Repo stats ─────────────────────────────────────────────────────────────────

@dataclass
class RepoStats:
    """Statistical summary for a scanned repository."""
    repo_name: str
    total_files: int
    production_files: int
    test_files: int
    generated_files: int

    # Raw score distribution (production files)
    mean_likelihood: float
    median_likelihood: float
    std_dev: float
    p25: float
    p75: float
    p90: float

    # Adjusted score distribution (production logic only)
    mean_adjusted: float
    median_adjusted: float
    kpi_score: float          # AI-adoption proxy KPI (adjusted, prod logic only)

    # Risk
    mean_risk: float
    high_risk_count: int

    # Classification counts (production files)
    ai_like_count: int
    human_like_count: int
    mixed_count: int
    uncertain_count: int

    # Top files
    top_ai_files: List[FileAnalysis] = field(default_factory=list)
    top_risk_files: List[FileAnalysis] = field(default_factory=list)
    top_human_files: List[FileAnalysis] = field(default_factory=list)

    # Git signals (optional)
    git_signals: dict = field(default_factory=dict)

    # Module breakdown
    module_summaries: List[ModuleSummary] = field(default_factory=list)

    # Category breakdown
    category_summaries: List[CategorySummary] = field(default_factory=list)

    # Data quality
    data_quality_score: float = 1.0  # [0, 1] — how complete was the analysis?
    exclusions: dict = field(default_factory=dict)

    @property
    def ai_like_pct(self) -> float:
        return self.ai_like_count / max(self.production_files, 1) * 100

    @property
    def summary_label(self) -> str:
        if self.kpi_score > 0.55:
            return "Elevated AI-like pattern density"
        if self.kpi_score > 0.40:
            return "Moderate AI-like patterns"
        if self.kpi_score > 0.25:
            return "Low AI-like signal density"
        return "Predominantly human-like patterns"

    def as_dict(self) -> dict:
        return {
            "repo_name":         self.repo_name,
            "total_files":       self.total_files,
            "production_files":  self.production_files,
            "test_files":        self.test_files,
            "generated_files":   self.generated_files,
            "kpi_score":         round(self.kpi_score, 4),
            "summary_label":     self.summary_label,
            "mean_likelihood":   round(self.mean_likelihood, 4),
            "median_likelihood": round(self.median_likelihood, 4),
            "mean_adjusted":     round(self.mean_adjusted, 4),
            "median_adjusted":   round(self.median_adjusted, 4),
            "std_dev":           round(self.std_dev, 4),
            "p25":               round(self.p25, 4),
            "p75":               round(self.p75, 4),
            "p90":               round(self.p90, 4),
            "ai_like_pct":       round(self.ai_like_pct, 2),
            "ai_like_count":     self.ai_like_count,
            "human_like_count":  self.human_like_count,
            "mixed_count":       self.mixed_count,
            "uncertain_count":   self.uncertain_count,
            "mean_risk":         round(self.mean_risk, 4),
            "high_risk_count":   self.high_risk_count,
            "data_quality_score": round(self.data_quality_score, 4),
            "exclusions":        self.exclusions,
            "module_summaries":  [m.as_dict() for m in self.module_summaries],
            "category_summaries": [c.as_dict() for c in self.category_summaries],
            "git_signals":       self.git_signals,
        }


# ── Percentile ─────────────────────────────────────────────────────────────────

def _percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


# ── Module aggregation ─────────────────────────────────────────────────────────

def _compute_module_summaries(analyses: List[FileAnalysis]) -> List[ModuleSummary]:
    """Aggregate file analyses by module path (package/folder)."""
    by_module: Dict[str, List[FileAnalysis]] = defaultdict(list)
    for a in analyses:
        key = a.module_path or "(root)"
        by_module[key].append(a)

    summaries = []
    for module_path, files in sorted(by_module.items()):
        adjusted_scores = [f.adjusted_score for f in files]
        risk_scores = [f.risk_score for f in files]
        ai_count = sum(1 for f in files if f.classification == "AI-like")
        langs = list(set(f.language for f in files))

        top_files = [
            f.path for f in sorted(files, key=lambda x: -x.adjusted_score)[:3]
        ]

        summaries.append(ModuleSummary(
            module_path=module_path,
            file_count=len(files),
            mean_adjusted=statistics.mean(adjusted_scores) if adjusted_scores else 0.0,
            median_adjusted=statistics.median(adjusted_scores) if adjusted_scores else 0.0,
            mean_risk=statistics.mean(risk_scores) if risk_scores else 0.0,
            ai_like_count=ai_count,
            languages=langs,
            top_files=top_files,
        ))

    return sorted(summaries, key=lambda m: -m.mean_adjusted)


# ── Category aggregation ───────────────────────────────────────────────────────

def _compute_category_summaries(analyses: List[FileAnalysis]) -> List[CategorySummary]:
    by_category: Dict[str, List[FileAnalysis]] = defaultdict(list)
    for a in analyses:
        by_category[a.category.value].append(a)

    summaries = []
    for cat, files in sorted(by_category.items()):
        if not files:
            continue
        summaries.append(CategorySummary(
            category=cat,
            file_count=len(files),
            mean_adjusted=statistics.mean(f.adjusted_score for f in files),
            mean_confidence=statistics.mean(f.confidence for f in files),
        ))
    return summaries


# ── Data quality score ─────────────────────────────────────────────────────────

def _compute_data_quality(
    analyses: List[FileAnalysis],
    has_git: bool,
    has_ast: bool,
) -> float:
    """
    Estimate data quality of the analysis.
    Lower when: no git, no AST, many low-confidence files, small files dominate.
    Returns [0.0, 1.0].
    """
    quality = 1.0

    if not has_git:
        quality -= 0.10
    if not has_ast:
        quality -= 0.05

    if not analyses:
        return max(0.0, quality)

    low_conf_ratio = sum(1 for a in analyses if a.confidence < 0.40) / len(analyses)
    quality -= low_conf_ratio * 0.20

    small_ratio = sum(1 for a in analyses if a.lines < 30) / len(analyses)
    quality -= small_ratio * 0.10

    return round(max(0.0, min(1.0, quality)), 4)


# ── Main calibration function ──────────────────────────────────────────────────

def calibrate_repo(
    repo_name: str,
    analyses: List[FileAnalysis],
    git_signals: Optional[dict] = None,
    has_git: bool = False,
    has_ast: bool = False,
) -> RepoStats:
    """
    Compute statistical calibration for a repo's file analyses.

    v4.0: Separates by category, computes module summaries, adds KPI score,
    risk stats, and data quality score.
    """
    prod   = [a for a in analyses if a.kind == "production"]
    tests  = [a for a in analyses if a.kind == "test"]
    generated = [a for a in analyses if a.category in (
        FileCategory.GENERATED, FileCategory.VENDOR
    )]

    # KPI-eligible = production + test, excluding generated/vendor/example
    kpi_eligible = [
        a for a in analyses
        if a.category not in (FileCategory.GENERATED, FileCategory.VENDOR, FileCategory.EXAMPLE)
    ]

    # Production logic only (highest weight in KPI)
    prod_logic = [a for a in prod if a.category == FileCategory.PRODUCTION_LOGIC]

    # Score distributions
    likelihoods = [a.ai_likelihood for a in prod] if prod else [0.0]
    adjusted    = [a.adjusted_score for a in kpi_eligible] if kpi_eligible else [0.0]
    kpi_scores  = [a.adjusted_score for a in prod_logic] if prod_logic else adjusted

    mean_lh    = statistics.mean(likelihoods)
    median_lh  = statistics.median(likelihoods)
    std_lh     = statistics.stdev(likelihoods) if len(likelihoods) > 1 else 0.0
    p25        = _percentile(likelihoods, 25)
    p75        = _percentile(likelihoods, 75)
    p90        = _percentile(likelihoods, 90)

    mean_adj   = statistics.mean(adjusted)
    median_adj = statistics.median(adjusted)
    kpi_score  = statistics.mean(kpi_scores)

    # Risk
    risks = [a.risk_score for a in analyses]
    mean_risk = statistics.mean(risks) if risks else 0.0
    high_risk_count = sum(1 for a in analyses if a.risk_score >= 0.60)

    # Classification counts (production files)
    counts = {"AI-like": 0, "human-like": 0, "mixed": 0, "uncertain": 0}
    for a in prod:
        counts[a.classification] = counts.get(a.classification, 0) + 1

    # Top files
    top_ai   = sorted(prod, key=lambda a: -a.adjusted_score)
    top_risk = sorted(analyses, key=lambda a: -a.risk_score)
    top_hum  = sorted(prod, key=lambda a: a.adjusted_score)

    top_ai   = [a for a in top_ai   if a.confidence >= 0.40][:5]
    top_risk = [a for a in top_risk if a.risk_score  >= 0.40][:5]
    top_hum  = [a for a in top_hum  if a.confidence >= 0.40][:5]

    # Module summaries (all non-generated files)
    non_gen = [a for a in analyses if a.category not in (FileCategory.GENERATED, FileCategory.VENDOR)]
    module_summaries = _compute_module_summaries(non_gen)

    # Category summaries
    category_summaries = _compute_category_summaries(analyses)

    # Exclusions transparency
    exclusions = {
        "generated_excluded": len(generated),
        "vendor_excluded":    sum(1 for a in analyses if a.category == FileCategory.VENDOR),
        "example_excluded":   sum(1 for a in analyses if a.category == FileCategory.EXAMPLE),
        "kpi_eligible":       len(kpi_eligible),
    }

    data_quality = _compute_data_quality(analyses, has_git=has_git, has_ast=has_ast)

    return RepoStats(
        repo_name=repo_name,
        total_files=len(analyses),
        production_files=len(prod),
        test_files=len(tests),
        generated_files=len(generated),
        mean_likelihood=round(mean_lh, 4),
        median_likelihood=round(median_lh, 4),
        std_dev=round(std_lh, 4),
        p25=round(p25, 4),
        p75=round(p75, 4),
        p90=round(p90, 4),
        mean_adjusted=round(mean_adj, 4),
        median_adjusted=round(median_adj, 4),
        kpi_score=round(kpi_score, 4),
        mean_risk=round(mean_risk, 4),
        high_risk_count=high_risk_count,
        ai_like_count=counts.get("AI-like", 0),
        human_like_count=counts.get("human-like", 0),
        mixed_count=counts.get("mixed", 0),
        uncertain_count=counts.get("uncertain", 0),
        top_ai_files=top_ai,
        top_risk_files=top_risk,
        top_human_files=top_hum,
        git_signals=git_signals or {},
        module_summaries=module_summaries[:20],
        category_summaries=category_summaries,
        data_quality_score=data_quality,
        exclusions=exclusions,
    )


def assign_percentile_tier(analysis: FileAnalysis, repo_stats: RepoStats) -> str:
    lh = analysis.ai_likelihood
    if lh >= repo_stats.p90:        return "top-10%"
    if lh >= repo_stats.p75:        return "top-25%"
    if lh >= repo_stats.median_likelihood: return "above-median"
    if lh >= repo_stats.p25:        return "below-median"
    return "bottom-25%"
