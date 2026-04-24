"""
scoring/model.py — Non-linear scoring model with calibrated confidence.

Design principles:
  - Non-linear signal aggregation (power scaling)
  - Sigmoid output for smooth 0–1 likelihood
  - Confidence from signal agreement, not just magnitude
  - Classification uses confidence-gated thresholds

⚠ OUTPUT DISCLAIMER: ai_likelihood is a probabilistic pattern score,
NOT a proof of AI authorship. Results are indicative only.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from ..config import ALL_SIGNAL_KEYS, get_weights


POWER_EXPONENT = 1.15   # non-linear scaling: contribution = w * s^1.15
SIGMOID_STEEPNESS = 7.0  # sigmoid sharpness around 0.5

# Classification thresholds (applied after confidence gating)
THRESH_AI_HIGH    = 0.68
THRESH_AI_LOW     = 0.62
THRESH_HUMAN_HIGH = 0.32
THRESH_HUMAN_LOW  = 0.38
MIN_CONFIDENCE    = 0.45  # below this → "uncertain" regardless of likelihood


@dataclass
class FileAnalysis:
    """Complete analysis result for a single file."""
    path: str
    language: str
    kind: str                      # production | test
    lines: int
    signals: Dict[str, float]      # all signal values [0.0, 1.0]
    raw_score: float               # weighted non-linear aggregate [0.0, 1.0]
    ai_likelihood: float           # sigmoid-mapped [0.0, 1.0]
    confidence: float              # signal agreement [0.0, 1.0]
    classification: str            # AI-like | human-like | mixed | uncertain
    top_signals: Dict[str, float]  # top-3 contributing signals

    def as_dict(self) -> dict:
        return {
            "path":           self.path,
            "language":       self.language,
            "kind":           self.kind,
            "lines":          self.lines,
            "ai_likelihood":  round(self.ai_likelihood, 3),
            "confidence":     round(self.confidence, 3),
            "classification": self.classification,
            "raw_score":      round(self.raw_score, 3),
            "top_signals":    {k: round(v, 3) for k, v in self.top_signals.items()},
            "all_signals":    {k: round(v, 3) for k, v in self.signals.items()},
        }


def _sigmoid(x: float, k: float = SIGMOID_STEEPNESS) -> float:
    """Sigmoid function: maps any real to (0, 1). Centered at x=0.5."""
    try:
        return 1.0 / (1.0 + math.exp(-k * (x - 0.5)))
    except OverflowError:
        return 0.0 if x < 0.5 else 1.0


def _signal_agreement(signals: Dict[str, float], weights: object, raw_score: float) -> float:
    """
    Confidence = fraction of weighted signal mass that agrees with the raw_score direction.
    If raw_score > 0.5 (AI-leaning): what fraction of weighted signals are also > 0.5?
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


def score_file(
    path: Path,
    language: str,
    kind: str,
    lines: int,
    signals: Dict[str, float],
) -> FileAnalysis:
    """
    Aggregate signals into a scored FileAnalysis.

    signals: dict of ALL_SIGNAL_KEYS → float [0.0, 1.0]
    Missing keys default to 0.40 (neutral).
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

    # Classification
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

    return FileAnalysis(
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
    )
