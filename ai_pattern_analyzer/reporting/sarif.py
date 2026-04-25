"""
reporting/sarif.py — SARIF 2.1.0 output extension point.

SARIF (Static Analysis Results Interchange Format) allows findings to
integrate with code scanning systems (GitHub Advanced Security, Azure DevOps,
VS Code SARIF Viewer, etc.).

Current implementation:
  - Generates valid SARIF 2.1.0 for findings with severity >= "moderate"
  - Includes rule definitions with help text and alternative explanations
  - Uses "none" kind for informational findings (pattern signals, not bugs)
  - Does NOT claim AI authorship in rule descriptions

Extension points:
  - Add rulesets per language by extending RULE_DEFINITIONS
  - Wire to GitHub Advanced Security by pushing sarif_output to PR check
  - Add suppression handling by marking suppressed rules with notApplicable

Reference: https://docs.oasis-open.org/sarif/sarif/v2.1.0/
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..scoring.model import FileAnalysis
from ..config import ANALYZER_VERSION, SCORING_MODEL_VERSION


TOOL_NAME = "ai-pattern-analyzer"
TOOL_VERSION = ANALYZER_VERSION
SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

# SARIF severity levels
_SEVERITY_MAP = {
    "high":     "error",
    "moderate": "warning",
    "low":      "note",
    "info":     "none",
}


def _build_rule(rule_id: str, description: str, alternatives: List[str]) -> Dict[str, Any]:
    """Build a SARIF rule definition."""
    return {
        "id": rule_id,
        "name": rule_id.replace(".", "_").replace("-", "_"),
        "shortDescription": {"text": description},
        "fullDescription": {
            "text": (
                f"{description}. "
                "This is a heuristic pattern signal — not proof of AI authorship. "
                + (" Possible alternative explanations: " + "; ".join(alternatives[:2]) + "."
                   if alternatives else "")
            )
        },
        "help": {
            "text": (
                "This finding reflects a code pattern statistically associated with "
                "AI-assisted or generated code. It should be interpreted alongside "
                "context: file category, framework conventions, and team coding standards."
            ),
            "markdown": (
                "**AI-like pattern signal** — heuristic indicator only. "
                "See [methodology](https://github.com/your-org/ai-tools#methodology) "
                "for interpretation guidance."
            ),
        },
        "properties": {
            "tags": ["ai-pattern", "heuristic"],
            "precision": "medium",
        },
    }


def _build_result(
    rule_id: str,
    severity_sarif: str,
    file_path: str,
    message: str,
    contribution: float,
) -> Dict[str, Any]:
    """Build a SARIF result (finding)."""
    return {
        "ruleId": rule_id,
        "kind":   "open" if severity_sarif in ("error", "warning") else "informational",
        "level":  severity_sarif,
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": file_path, "uriBaseId": "%SRCROOT%"},
                    "region": {"startLine": 1},
                }
            }
        ],
        "properties": {
            "score_contribution": round(contribution, 4),
        },
    }


def build_sarif_report(
    all_analyses: Dict[str, List[FileAnalysis]],
    min_severity: str = "moderate",
) -> Dict[str, Any]:
    """
    Build a SARIF 2.1.0 report from file analyses.

    Only includes findings with severity >= min_severity.
    Results with kind=none are informational (pattern signals).

    Extension point: To push to GitHub Advanced Security, serialize to JSON
    and use the upload-sarif GitHub Action.
    """
    severity_rank = {"info": 0, "low": 1, "moderate": 2, "high": 3}
    min_rank = severity_rank.get(min_severity, 2)

    rules: Dict[str, Dict] = {}
    results: List[Dict] = []

    for repo_name, analyses in all_analyses.items():
        for analysis in analyses:
            for finding in analysis.findings:
                if severity_rank.get(finding.severity, 0) < min_rank:
                    continue

                rule_id = finding.rule_id
                if rule_id not in rules:
                    alternatives = [ae.explanation for ae in finding.alternative_explanations]
                    rules[rule_id] = _build_rule(rule_id, finding.description, alternatives)

                severity_sarif = _SEVERITY_MAP.get(finding.severity, "note")
                rel_path = analysis.path

                msg = (
                    f"{finding.description} "
                    f"(contribution={finding.score_contribution:.3f}, "
                    f"confidence={finding.confidence:.2f}). "
                    "This is a heuristic pattern signal — see alternative explanations."
                )

                results.append(_build_result(
                    rule_id=rule_id,
                    severity_sarif=severity_sarif,
                    file_path=rel_path,
                    message=msg,
                    contribution=finding.score_contribution,
                ))

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name":            TOOL_NAME,
                        "version":         TOOL_VERSION,
                        "informationUri":  "https://github.com/your-org/ai-tools",
                        "rules":           list(rules.values()),
                        "properties": {
                            "scoring_model_version": SCORING_MODEL_VERSION,
                            "disclaimer": (
                                "This tool detects heuristic code patterns — "
                                "not AI authorship. Results are probabilistic indicators only."
                            ),
                        },
                    }
                },
                "results": results,
                "artifacts": [
                    {"location": {"uri": a.path, "uriBaseId": "%SRCROOT%"}}
                    for analyses in all_analyses.values()
                    for a in analyses
                ],
            }
        ],
    }


def write_sarif(report: dict, output_path: Path) -> None:
    """Write SARIF report to file."""
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
