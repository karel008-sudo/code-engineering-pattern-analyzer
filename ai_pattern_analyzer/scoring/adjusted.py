"""
scoring/adjusted.py — Context-aware score adjustment layer.

Applies category and framework context to raw scores to produce:
  - adjusted_score: raw_score modified for category/framework context
  - risk_score: engineering risk combining AI-likeness + criticality + test coverage

Design:
  - Raw score reflects heuristic signals only
  - Adjusted score accounts for file category, framework boilerplate,
    DTO/mapper nature, and generated code patterns
  - Risk score is separate from AI-likeness; it reflects the engineering
    risk of the file needing manual review

Extension points:
  - Business criticality modifier: configure via critical_paths in ScanConfig
  - Test coverage context: wire test coverage adapter here
  - Mutation testing context: wire mutation results here

⚠ Adjusted score is still a heuristic estimate, not proof of AI origin.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from ..domain import (
    FileCategory,
    FrameworkContext,
    ScoreBreakdown,
)


# ── Category-based adjustment ─────────────────────────────────────────────────

def apply_category_adjustment(raw_score: float, category: FileCategory) -> float:
    """
    Apply category context to raw score.
    DTOs, mappers, generated files naturally score high on AI-like signals
    because they are inherently regular and structured.
    """
    factor = category.adjustment_factor
    adjusted = raw_score * factor
    return round(max(0.0, min(1.0, adjusted)), 4)


# ── Framework-based adjustment ────────────────────────────────────────────────

def apply_framework_adjustment(
    raw_score: float,
    ctx: Optional[FrameworkContext],
) -> tuple[float, float]:
    """
    Apply framework context adjustment to raw score.

    Returns (adjusted_score, framework_adj_amount) where:
      adjusted_score  = score after framework context reduction
      framework_adj   = how much the framework reduced the score (negative = reduced)
    """
    if ctx is None or not ctx.detected_frameworks:
        return raw_score, 0.0

    boilerplate = ctx.boilerplate_score

    # Framework boilerplate directly suppresses the score
    # High boilerplate = framework explains the patterns, not AI
    reduction = boilerplate * 0.30  # max 30% reduction from framework context

    if ctx.is_mapstruct_mapper or ctx.is_openapi_generated:
        reduction = max(reduction, 0.35)

    adjusted = raw_score * (1.0 - reduction)
    framework_adj = adjusted - raw_score  # negative value (reduction)

    return round(max(0.0, min(1.0, adjusted)), 4), round(framework_adj, 4)


# ── Risk score ────────────────────────────────────────────────────────────────

def compute_risk_score(
    adjusted_score: float,
    confidence: float,
    category: FileCategory,
    is_critical_path: bool = False,
    framework_ctx: Optional[FrameworkContext] = None,
) -> float:
    """
    Compute engineering risk score. This is separate from AI-likeness.

    Risk combines:
      - adjusted AI-like signal (higher score = higher risk of needing review)
      - confidence (low confidence = uncertain = lower risk claim)
      - file category (production logic at higher risk than DTOs)
      - critical path flag (configured via ScanConfig.critical_paths)

    Risk score is NOT a claim of AI origin — it prioritizes which files
    should receive manual engineering review.

    Returns [0.0, 1.0] where 1.0 = high review priority.
    """
    if category in (FileCategory.GENERATED, FileCategory.VENDOR):
        return 0.0

    # Base risk from adjusted score
    base_risk = adjusted_score * confidence

    # Category multiplier — production logic risk is highest
    category_multiplier = {
        FileCategory.PRODUCTION_LOGIC:  1.00,
        FileCategory.DTO_MAPPER:        0.40,
        FileCategory.TEST:              0.55,
        FileCategory.CONFIG_INFRA:      0.45,
        FileCategory.MIGRATION:         0.60,
        FileCategory.EXAMPLE:           0.20,
        FileCategory.NOTEBOOK:          0.35,
        FileCategory.BOILERPLATE_INTEG: 0.35,
        FileCategory.UNKNOWN:           0.80,
        FileCategory.GENERATED:         0.00,
        FileCategory.VENDOR:            0.00,
    }.get(category, 0.60)

    risk = base_risk * category_multiplier

    # Critical path boost
    if is_critical_path:
        risk = risk * 1.35

    # Framework boilerplate reduces risk (framework explains patterns)
    if framework_ctx and framework_ctx.boilerplate_score > 0.5:
        risk = risk * 0.60

    return round(max(0.0, min(1.0, risk)), 4)


# ── Confidence model ──────────────────────────────────────────────────────────

def compute_uncertainty_reasons(
    signals: dict,
    category: FileCategory,
    framework_ctx: Optional[FrameworkContext],
    has_git: bool,
    lines: int,
    confidence: float,
) -> List[str]:
    """
    Generate human-readable uncertainty reasons for a file analysis.
    These appear in reports to explain why confidence may be reduced.
    """
    reasons = []

    if lines < 30:
        reasons.append("Very small file — insufficient signal evidence (< 30 lines)")
    elif lines < 50:
        reasons.append("Small file — limited signal evidence (< 50 lines)")

    if not has_git:
        reasons.append("No Git history available — temporal signals excluded")

    if category == FileCategory.DTO_MAPPER:
        reasons.append(
            "DTO/mapper category — elevated signals may reflect structural regularity, "
            "not AI generation"
        )
    elif category == FileCategory.GENERATED:
        reasons.append(
            "File marked as generated — score excluded from KPI; "
            "classification not meaningful"
        )
    elif category == FileCategory.BOILERPLATE_INTEG:
        reasons.append(
            "Framework integration boilerplate — elevated signals are expected by "
            "framework convention"
        )

    if framework_ctx and framework_ctx.detected_frameworks:
        fws = ", ".join(framework_ctx.detected_frameworks)
        reasons.append(
            f"Framework(s) detected ({fws}) — some AI-like signals may be explained by "
            "framework conventions"
        )

    if confidence < 0.45:
        reasons.append(
            f"Low signal agreement (confidence={confidence:.2f}) — signals point in "
            "different directions; interpretation unreliable"
        )

    active_signals = sum(
        1 for k, v in signals.items()
        if v > 0.0 and k not in ("placeholder_density", "prompt_residue")
    )
    if active_signals < 4:
        reasons.append(
            f"Only {active_signals} active signals — limited signal coverage for this file"
        )

    return reasons


# ── Full score computation ────────────────────────────────────────────────────

def build_score_breakdown(
    raw_score: float,
    confidence: float,
    category: FileCategory,
    framework_ctx: Optional[FrameworkContext],
    signals: dict,
    is_critical_path: bool = False,
    has_git: bool = False,
    lines: int = 0,
) -> ScoreBreakdown:
    """
    Build the complete score breakdown from raw signals.
    This is the single entry point for computing adjusted_score and risk_score.
    """
    # Step 1: category adjustment
    cat_adjusted = apply_category_adjustment(raw_score, category)
    category_adj = cat_adjusted - raw_score  # negative when reduced

    # Step 2: framework adjustment
    fw_adjusted, framework_adj = apply_framework_adjustment(cat_adjusted, framework_ctx)

    # Final adjusted score (bounded)
    adjusted_score = max(0.0, min(1.0, fw_adjusted))

    # Risk score
    risk_score = compute_risk_score(
        adjusted_score=adjusted_score,
        confidence=confidence,
        category=category,
        is_critical_path=is_critical_path,
        framework_ctx=framework_ctx,
    )

    # Uncertainty reasons
    uncertainty_reasons = compute_uncertainty_reasons(
        signals=signals,
        category=category,
        framework_ctx=framework_ctx,
        has_git=has_git,
        lines=lines,
        confidence=confidence,
    )

    return ScoreBreakdown(
        raw_score=round(raw_score, 4),
        adjusted_score=round(adjusted_score, 4),
        category_adj=round(category_adj, 4),
        framework_adj=round(framework_adj, 4),
        confidence=round(confidence, 4),
        risk_score=round(risk_score, 4),
        uncertainty_reasons=uncertainty_reasons,
    )


# ── Counterfactual score estimation ───────────────────────────────────────────

def counterfactual_score(signals: dict, language: str, exclude_keys: List[str]) -> float:
    """
    Extension point: Compute a score excluding certain signal groups.
    Used for ablation analysis and sensitivity testing.

    Returns approximate adjusted score without the excluded signals.
    This is a simplified re-computation without full pipeline.
    """
    from ..config import get_weights
    from ..scoring.model import POWER_EXPONENT, _sigmoid

    weights = get_weights(language)
    filtered = {k: v for k, v in signals.items() if k not in exclude_keys}

    raw = 0.0
    for key, w in weights.items():
        if w <= 0 or key in exclude_keys:
            continue
        sig = filtered.get(key, 0.40)
        raw += w * (sig ** POWER_EXPONENT)

    raw = max(0.0, min(1.0, raw))
    return round(_sigmoid(raw), 4)
