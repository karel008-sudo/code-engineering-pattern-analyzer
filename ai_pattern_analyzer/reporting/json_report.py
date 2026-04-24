"""
reporting/json_report.py — Structured JSON output with full signal detail.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..scoring.calibration import RepoStats
from ..scoring.model import FileAnalysis


SCHEMA_VERSION = "3.0"

DISCLAIMER_TEXT = (
    "This tool detects code-generation PATTERNS using statistical heuristics. "
    "It does NOT identify authorship, prove AI use, or constitute evidence for any claim. "
    "Results are probabilistic and should be interpreted as trend indicators only."
)


def build_report(
    all_stats: List[RepoStats],
    all_analyses: Dict[str, List[FileAnalysis]],
    cli_args: Optional[dict] = None,
) -> Dict[str, Any]:
    """Build a complete JSON-serializable report."""
    repos_out = []
    for stats in all_stats:
        analyses = all_analyses.get(stats.repo_name, [])
        repos_out.append({
            "repo":         stats.repo_name,
            "summary": {
                "label":             stats.summary_label,
                "production_files":  stats.production_files,
                "test_files":        stats.test_files,
                "median_likelihood": stats.median_likelihood,
                "mean_likelihood":   stats.mean_likelihood,
                "std_dev":           stats.std_dev,
                "p25":               stats.p25,
                "p75":               stats.p75,
                "p90":               stats.p90,
                "ai_like_pct":       round(stats.ai_like_pct, 2),
            },
            "classification_counts": {
                "AI-like":    stats.ai_like_count,
                "human-like": stats.human_like_count,
                "mixed":      stats.mixed_count,
                "uncertain":  stats.uncertain_count,
            },
            "git_signals":  stats.git_signals,
            "files": [a.as_dict() for a in analyses],
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "disclaimer":     DISCLAIMER_TEXT,
        "invocation":     cli_args or {},
        "repos":          repos_out,
    }


def write_json(report: dict, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_csv(
    all_analyses: Dict[str, List[FileAnalysis]],
    output_path: Path,
) -> None:
    """Write per-file CSV with key columns."""
    lines = ["repo,file,language,kind,lines,ai_likelihood,confidence,classification"]
    for repo, analyses in all_analyses.items():
        for a in analyses:
            rel = Path(a.path).name
            lines.append(
                f"{repo},{rel},{a.language},{a.kind},{a.lines},"
                f"{a.ai_likelihood:.4f},{a.confidence:.4f},{a.classification}"
            )
    output_path.write_text("\n".join(lines), encoding="utf-8")
