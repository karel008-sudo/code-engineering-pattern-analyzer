"""
scoring/model.py — Non-linear scoring model with calibrated confidence.

v5.0 additions:
  - FileAnalysis now carries origin_estimate (three-way AI/human probability)
  - scaffold_score, style_continuity, magic_number_score, name_body_coherence
    computed in pipeline.py and passed into score_file()

v4.0 additions:
  - FileAnalysis now carries category, adjusted_score, risk_score,
    score_breakdown, framework_context, findings, uncertainty_reasons

Design principles:
  - Non-linear signal aggregation (power scaling)
  - Sigmoid output for smooth 0–1 likelihood
  - Confidence from signal agreement, not just magnitude
  - Classification uses confidence-gated thresholds
  - raw_score = heuristic aggregate; adjusted_score = context-aware

⚠ OUTPUT DISCLAIMER: ai_likelihood / adjusted_score and origin_estimate are
  probabilistic pattern signals, NOT proof of AI authorship. Results are
  directional estimates only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import (
    ALL_SIGNAL_KEYS,
    ANALYZER_VERSION,
    SCORING_MODEL_VERSION,
    RULESET_VERSION,
    get_weights,
)
from ..domain import (
    FileCategory,
    FrameworkContext,
    OriginEstimate,
    ScoreBreakdown,
    Finding,
    AlternativeExplanation,
    Evidence,
    score_band_from_likelihood,
    review_recommendation,
)
from .adjusted import build_score_breakdown


POWER_EXPONENT    = 1.15   # non-linear scaling: contribution = w * s^1.15
SIGMOID_STEEPNESS = 7.0    # sigmoid sharpness around 0.5

# Classification thresholds (applied after confidence gating)
THRESH_AI_HIGH    = 0.68
THRESH_AI_LOW     = 0.62
THRESH_HUMAN_HIGH = 0.32
THRESH_HUMAN_LOW  = 0.38
MIN_CONFIDENCE    = 0.45   # below this → "uncertain" regardless of likelihood


@dataclass
class FileAnalysis:
    """
    Complete analysis result for a single file.

    v4.0 additions:
      - category: semantic file category (production_logic, dto, test, etc.)
      - adjusted_score: raw_score adjusted for category/framework context
      - risk_score: engineering review priority (≠ AI-likeness)
      - score_breakdown: detailed breakdown with uncertainty reasons
      - framework_context: detected frameworks and boilerplate context
      - findings: list of individual rule findings with evidence
      - uncertainty_reasons: human-readable confidence reduction reasons
      - module_path: relative module/package path
    """
    path: str
    language: str
    kind: str                          # "production" | "test" (legacy, kept for compat)
    lines: int
    signals: Dict[str, float]          # all signal values [0.0, 1.0]
    raw_score: float                   # weighted non-linear aggregate [0.0, 1.0]
    ai_likelihood: float               # sigmoid-mapped raw score [0.0, 1.0]
    confidence: float                  # signal agreement [0.0, 1.0]
    classification: str                # AI-like | human-like | mixed | uncertain
    top_signals: Dict[str, float]      # top-4 contributing signals

    # v4.0 fields
    category: FileCategory = FileCategory.UNKNOWN
    adjusted_score: float = 0.0        # context-adjusted score [0.0, 1.0]
    risk_score: float = 0.0            # engineering review risk [0.0, 1.0]
    score_breakdown: Optional[ScoreBreakdown] = None
    framework_context: Optional[FrameworkContext] = None
    findings: List[Finding] = field(default_factory=list)
    uncertainty_reasons: List[str] = field(default_factory=list)
    module_path: str = ""

    # v5.0 fields
    origin_estimate: Optional[OriginEstimate] = None  # three-way AI/human probability
    scaffold_score: float = 0.0        # scaffold completeness [0.0, 1.0]
    style_continuity: float = 1.0      # style continuity [0.0, 1.0]
    magic_number_score: float = 0.5    # magic number discipline [0.0, 1.0]
    name_body_coherence: float = 0.5   # name-to-body coherence [0.0, 1.0]

    @property
    def score_band(self) -> str:
        return score_band_from_likelihood(self.adjusted_score)

    @property
    def review_recommendation(self) -> str:
        return review_recommendation(
            self.adjusted_score, self.risk_score, self.category, self.confidence
        )

    def as_dict(self, include_snippets: bool = False) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "path":              self.path,
            "language":          self.language,
            "category":          self.category.value,
            "kind":              self.kind,
            "lines":             self.lines,
            "module_path":       self.module_path,
            # Scores
            "ai_likelihood":     round(self.ai_likelihood, 3),
            "adjusted_score":    round(self.adjusted_score, 3),
            "risk_score":        round(self.risk_score, 3),
            "confidence":        round(self.confidence, 3),
            "score_band":        self.score_band,
            "classification":    self.classification,
            "raw_score":         round(self.raw_score, 3),
            # Explainability
            "top_signals":       {k: round(v, 3) for k, v in self.top_signals.items()},
            "all_signals":       {k: round(v, 3) for k, v in self.signals.items()},
            "findings_count":    len(self.findings),
            "uncertainty_reasons": self.uncertainty_reasons,
            "review_recommendation": self.review_recommendation,
            # Versioning
            "scoring_model_version": SCORING_MODEL_VERSION,
        }
        if self.score_breakdown:
            d["score_breakdown"] = self.score_breakdown.as_dict()
        if self.framework_context:
            d["framework_context"] = self.framework_context.as_dict()
        if self.origin_estimate:
            d["origin_estimate"] = self.origin_estimate.as_dict()
        d["findings"] = [f.as_dict() for f in self.findings]
        return d


def _sigmoid(x: float, k: float = SIGMOID_STEEPNESS) -> float:
    """Sigmoid function mapping any real to (0, 1), centered at x=0.5."""
    try:
        return 1.0 / (1.0 + math.exp(-k * (x - 0.5)))
    except OverflowError:
        return 0.0 if x < 0.5 else 1.0


def _signal_agreement(
    signals: Dict[str, float],
    weights: object,
    raw_score: float,
) -> float:
    """
    Confidence = fraction of weighted signal mass that agrees with direction.
    If raw_score > 0.5 (AI-leaning): what fraction of weighted signals are > 0.5?
    """
    direction = raw_score > 0.5
    total_weight = 0.0
    agreeing_weight = 0.0

    for key, w in weights.items():
        if w <= 0:
            continue
        sig_val = signals.get(key, 0.5)
        total_weight += w
        if (sig_val > 0.5) == direction:
            agreeing_weight += w

    if total_weight == 0:
        return 0.0
    return agreeing_weight / total_weight


def _build_findings(
    signals: Dict[str, float],
    contributions: Dict[str, float],
    language: str,
    framework_ctx: Optional[FrameworkContext],
) -> List[Finding]:
    """
    Build Finding objects from signal contributions.
    Findings are generated for signals that exceed a contribution threshold.
    """
    from .._signal_metadata import SIGNAL_METADATA

    findings = []
    fw_explanations = []
    if framework_ctx:
        from ..analyzers.framework import get_alternative_explanations
        fw_explanations = get_alternative_explanations(framework_ctx)

    for key, contribution in sorted(contributions.items(), key=lambda x: -x[1]):
        if contribution < 0.01:
            continue

        sig_value = signals.get(key, 0.0)
        if sig_value < 0.35:
            continue

        meta = SIGNAL_METADATA.get(key, {})
        severity = "info"
        if contribution > 0.06:
            severity = "high"
        elif contribution > 0.03:
            severity = "moderate"
        elif contribution > 0.01:
            severity = "low"

        evidence = [Evidence(
            kind="statistic",
            description=f"Signal value: {sig_value:.2f}, weight contribution: {contribution:.3f}",
            value=sig_value,
        )]

        # Combine framework and signal-specific alternative explanations
        alt_explanations = list(fw_explanations)
        for ae in meta.get("alternative_explanations", []):
            alt_explanations.append(AlternativeExplanation(ae[0], ae[1]))

        finding = Finding(
            rule_id=f"signal.{key}",
            category=meta.get("category", "heuristic"),
            description=meta.get("description", key.replace("_", " ").title()),
            score_contribution=round(contribution, 4),
            confidence=round(min(sig_value, 0.90), 4),
            severity=severity,
            evidence=evidence,
            alternative_explanations=alt_explanations[:3],  # cap at 3 per finding
            tags=meta.get("tags", [language]),
        )
        findings.append(finding)

    return findings[:10]  # top 10 findings max


def score_file(
    path: Path,
    language: str,
    kind: str,
    lines: int,
    signals: Dict[str, float],
    category: FileCategory = FileCategory.UNKNOWN,
    framework_ctx: Optional[FrameworkContext] = None,
    is_critical_path: bool = False,
    has_git: bool = False,
    module_path: str = "",
    # v5.0 origin estimate inputs
    scaffold_score: float = 0.0,
    style_continuity: float = 1.0,
    magic_number_score: float = 0.5,
    name_body_coherence: float = 0.5,
) -> FileAnalysis:
    """
    Aggregate signals into a scored FileAnalysis.

    signals:      dict of ALL_SIGNAL_KEYS → float [0.0, 1.0]
    category:     semantic file category (affects adjusted score)
    framework_ctx: detected framework context (affects adjusted score)

    v5.0: scaffold_score, style_continuity, magic_number_score, name_body_coherence
    are passed from pipeline.py to compute the OriginEstimate (three-way probability).

    Missing signal keys default to 0.40 (neutral).
    """
    weights = get_weights(language)

    # Fill missing signals with neutral value
    full_signals = {k: signals.get(k, 0.40) for k in ALL_SIGNAL_KEYS}

    # Non-linear weighted aggregation
    raw_score = 0.0
    contributions: Dict[str, float] = {}
    for key, w in weights.items():
        if w <= 0:
            continue
        sig = full_signals.get(key, 0.40)
        contribution = w * (sig ** POWER_EXPONENT)
        raw_score += contribution
        contributions[key] = contribution

    raw_score = max(0.0, min(1.0, raw_score))

    # Sigmoid output
    ai_likelihood = _sigmoid(raw_score)

    # Confidence from signal agreement
    confidence = _signal_agreement(full_signals, weights, raw_score)

    # Classification (with confidence gating)
    if confidence < MIN_CONFIDENCE:
        classification = "uncertain"
    elif ai_likelihood >= THRESH_AI_HIGH:
        classification = "AI-like"
    elif ai_likelihood >= THRESH_AI_LOW:
        classification = "mixed" if confidence < 0.65 else "AI-like"
    elif ai_likelihood <= THRESH_HUMAN_HIGH:
        classification = "human-like"
    elif ai_likelihood <= THRESH_HUMAN_LOW:
        classification = "mixed" if confidence < 0.65 else "human-like"
    else:
        classification = "mixed"

    # Top contributing signals (for explainability)
    top_signals = dict(
        sorted(contributions.items(), key=lambda x: -x[1])[:4]
    )

    # Build adjusted score and risk score
    score_breakdown = build_score_breakdown(
        raw_score=raw_score,
        confidence=confidence,
        category=category,
        framework_ctx=framework_ctx,
        signals=full_signals,
        is_critical_path=is_critical_path,
        has_git=has_git,
        lines=lines,
    )

    # Build findings
    findings = _build_findings(full_signals, contributions, language, framework_ctx)

    # v5.0: Build partial FileAnalysis first, then compute OriginEstimate
    analysis = FileAnalysis(
        path=str(path),
        language=language,
        kind=kind,
        lines=lines,
        signals=full_signals,
        raw_score=raw_score,
        ai_likelihood=ai_likelihood,
        confidence=confidence,
        classification=classification,
        top_signals=top_signals,
        # v4.0 fields
        category=category,
        adjusted_score=score_breakdown.adjusted_score,
        risk_score=score_breakdown.risk_score,
        score_breakdown=score_breakdown,
        framework_context=framework_ctx,
        findings=findings,
        uncertainty_reasons=score_breakdown.uncertainty_reasons,
        module_path=module_path,
        # v5.0 fields
        scaffold_score=scaffold_score,
        style_continuity=style_continuity,
        magic_number_score=magic_number_score,
        name_body_coherence=name_body_coherence,
    )

    # v5.0: Compute OriginEstimate (three-way probability)
    # IMPORTANT: Skip for GENERATED and VENDOR files.
    # Auto-generated code (protobuf, OpenAPI, jOOQ) and vendored third-party code
    # are excluded from the AI origin KPI entirely.  Computing an origin estimate
    # for them would be misleading — a protobuf stub is not "LLM-generated", it is
    # tool-generated, which is a fundamentally different concept.
    _SKIP_ORIGIN = (FileCategory.GENERATED, FileCategory.VENDOR)
    if category not in _SKIP_ORIGIN:
        try:
            from ..origin.engine import compute_file_origin
            analysis.origin_estimate = compute_file_origin(
                file_analysis=analysis,
                scaffold_score=scaffold_score,
                style_continuity=style_continuity,
                magic_number_score=magic_number_score,
                name_body_coherence=name_body_coherence,
            )
        except Exception:
            pass  # Origin estimate is optional; never fail the whole scan

    return analysis
