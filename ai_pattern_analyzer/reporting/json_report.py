"""
reporting/json_report.py — Structured JSON output with full signal detail.

v4.0 schema additions:
  - analyzer_version, scoring_model_version, ruleset_version
  - scan_metadata (config, timestamp, maturity)
  - data_quality per repo
  - category_summary and module_summary per repo
  - adjusted_score, risk_score, score_breakdown per file
  - framework_context per file
  - findings with evidence and alternative_explanations
  - uncertainty_reasons
  - exclusions transparency
  - limitations section

Schema version: 4.0
Machine-readable contract: stable field names, explicit version.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..scoring.calibration import RepoStats
from ..scoring.model import FileAnalysis
from ..config import ANALYZER_VERSION, SCORING_MODEL_VERSION, RULESET_VERSION


SCHEMA_VERSION = "5.0"

DISCLAIMER_TEXT = (
    "This tool detects code-generation PATTERNS using statistical heuristics. "
    "It does NOT identify authorship, prove AI use, or constitute evidence for any "
    "contractual, compliance, legal, or personnel claim. "
    "Results are probabilistic pattern signals and should be interpreted as "
    "directional trend indicators only. "
    "Scores labeled 'AI-like' reflect stylistic and structural code characteristics, "
    "not verified AI origin."
)

LIMITATIONS = [
    "Scores reflect heuristic pattern matching — not forensic AI detection",
    "False positives: senior clean code, strict formatters, DTOs, generated clients, "
    "framework boilerplate, heavy refactoring",
    "False negatives: AI code edited by human, Copilot incremental suggestions, "
    "terse AI code, intentionally irregular AI output",
    "No source code, metadata, or telemetry is sent to external services",
    "Analysis runs entirely locally — air-gapped compatible",
    "Results must not be used for individual developer evaluation or disciplinary action",
]


def build_report(
    all_stats: List[RepoStats],
    all_analyses: Dict[str, List[FileAnalysis]],
    cli_args: Optional[dict] = None,
    include_snippets: bool = False,
) -> Dict[str, Any]:
    """Build a complete JSON-serializable report."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    repos_out = []
    for stats in all_stats:
        analyses = all_analyses.get(stats.repo_name, [])
        repos_out.append(_build_repo(stats, analyses, include_snippets))

    # v5.0: Portfolio-level origin estimate
    portfolio_origin = _compute_portfolio_origin(all_stats)

    return {
        "schema_version":         SCHEMA_VERSION,
        "disclaimer":             DISCLAIMER_TEXT,
        "limitations":            LIMITATIONS,
        "analyzer_version":       ANALYZER_VERSION,
        "scoring_model_version":  SCORING_MODEL_VERSION,
        "ruleset_version":        RULESET_VERSION,
        "scan_metadata": {
            "timestamp":  now,
            "invocation": cli_args or {},
        },
        "portfolio_origin_estimate": portfolio_origin,
        "repos": repos_out,
    }


def _build_repo(
    stats: RepoStats,
    analyses: List[FileAnalysis],
    include_snippets: bool,
) -> Dict[str, Any]:
    return {
        "repo":           stats.repo_name,
        "summary":        stats.as_dict(),
        "origin_estimate": stats.origin_estimate.as_dict() if stats.origin_estimate else None,
        "data_quality": {
            "score":  stats.data_quality_score,
            "exclusions": stats.exclusions,
        },
        "git_signals":    stats.git_signals,
        "category_summary": [c.as_dict() for c in stats.category_summaries],
        "module_summary":   [m.as_dict() for m in stats.module_summaries],
        "files": [a.as_dict(include_snippets=include_snippets) for a in analyses],
        "top_risk_files": [
            _file_summary(a) for a in stats.top_risk_files
        ],
        "false_positive_candidates": _find_fp_candidates(analyses),
        "high_confidence_candidates": _find_hc_candidates(analyses),
    }


def _compute_portfolio_origin(all_stats: List[RepoStats]) -> Optional[Dict[str, Any]]:
    """Compute portfolio-wide origin estimate from all repo estimates.

    Uses kpi_eligible file count as weight — this matches the population
    that was actually used to compute each repo's origin_estimate.
    Using production_files would create a weight mismatch since the origin
    estimate also includes test files (which are kpi_eligible).
    """
    try:
        from ..origin.engine import aggregate_origin_estimates
        pairs = [
            # Weight by kpi_eligible (origin estimate population), not just production files
            (s.origin_estimate, s.exclusions.get("kpi_eligible", s.production_files))
            for s in all_stats
            if s.origin_estimate is not None
            and s.exclusions.get("kpi_eligible", s.production_files) > 0
        ]
        if not pairs:
            return None
        portfolio = aggregate_origin_estimates(pairs)
        result = portfolio.as_dict()
        result["methodology"] = (
            "Weighted average of per-repository origin estimates. "
            "Each repository weighted by production file count. "
            "These are heuristic estimates, not forensic proof."
        )
        result["caveats"] = [
            "Portfolio estimate aggregates heuristic signals across repositories.",
            "Vendor and generated files are excluded from KPI by default.",
            "Confidence may be lower for small or poorly-covered repositories.",
            "These percentages do not constitute proof of AI authorship.",
        ]
        return result
    except Exception:
        return None


def _file_summary(a: FileAnalysis) -> Dict[str, Any]:
    return {
        "path":           a.path,
        "language":       a.language,
        "category":       a.category.value,
        "adjusted_score": round(a.adjusted_score, 3),
        "risk_score":     round(a.risk_score, 3),
        "confidence":     round(a.confidence, 3),
        "classification": a.classification,
        "recommendation": a.review_recommendation,
    }


def _find_fp_candidates(analyses: List[FileAnalysis]) -> List[Dict]:
    """
    Identify likely false-positive candidates:
    high raw score but high framework boilerplate or DTO category.
    """
    candidates = []
    for a in analyses:
        if a.raw_score > 0.40 and a.adjusted_score < a.raw_score * 0.65:
            candidates.append({
                "path":          a.path,
                "category":      a.category.value,
                "raw_score":     round(a.raw_score, 3),
                "adjusted_score": round(a.adjusted_score, 3),
                "reason":        f"Category {a.category.value} reduces AI interpretation",
            })
    return candidates[:10]


def _find_hc_candidates(analyses: List[FileAnalysis]) -> List[Dict]:
    """
    High-confidence AI-like candidates:
    adjusted_score > 0.55, confidence > 0.60, production logic.
    """
    from ..domain import FileCategory
    candidates = [
        {
            "path":          a.path,
            "category":      a.category.value,
            "adjusted_score": round(a.adjusted_score, 3),
            "confidence":    round(a.confidence, 3),
            "risk_score":    round(a.risk_score, 3),
        }
        for a in analyses
        if (a.adjusted_score > 0.55
            and a.confidence > 0.60
            and a.category == FileCategory.PRODUCTION_LOGIC)
    ]
    return sorted(candidates, key=lambda x: -x["adjusted_score"])[:10]


def write_json(report: dict, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_csv(
    all_analyses: Dict[str, List[FileAnalysis]],
    output_path: Path,
) -> None:
    """Write per-file CSV with key columns including v4.0 fields."""
    lines = [
        "repo,file,language,category,kind,lines,"
        "ai_likelihood,adjusted_score,risk_score,confidence,classification,recommendation"
    ]
    for repo, analyses in all_analyses.items():
        for a in analyses:
            rel = Path(a.path).name
            lines.append(
                f"{repo},{rel},{a.language},{a.category.value},{a.kind},{a.lines},"
                f"{a.ai_likelihood:.4f},{a.adjusted_score:.4f},{a.risk_score:.4f},"
                f"{a.confidence:.4f},{a.classification},{a.review_recommendation}"
            )
    output_path.write_text("\n".join(lines), encoding="utf-8")
