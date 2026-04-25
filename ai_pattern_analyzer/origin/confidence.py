"""
origin/confidence.py — Confidence interval calculation for origin estimates.

Provides point-estimate uncertainty quantification for the three-way origin
probability model. Intervals are heuristic ranges, not frequentist confidence
intervals in the statistical sense.

IMPORTANT: These intervals express uncertainty in the heuristic model, not
statistical guarantees. They should be read as "the estimate could reasonably
move this far given the available evidence."
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceInterval:
    """
    A simple confidence interval for a percentage point estimate.

    Both ``low`` and ``high`` are clamped to [0, 100].

    Attributes:
        low:  Lower bound of the interval (percentage points, 0–100).
        high: Upper bound of the interval (percentage points, 0–100).
    """

    low: float
    high: float

    def __post_init__(self) -> None:
        self.low = max(0.0, min(100.0, self.low))
        self.high = max(0.0, min(100.0, self.high))

    @property
    def width(self) -> float:
        """Full width of the interval in percentage points."""
        return self.high - self.low

    def as_dict(self) -> dict:
        """Serialise to a plain dict with rounded values."""
        return {
            "low": round(self.low, 1),
            "high": round(self.high, 1),
        }


def compute_interval(
    point_estimate_pct: float,
    confidence_level: float,
    data_quality: float,
) -> ConfidenceInterval:
    """
    Compute a heuristic confidence interval around a percentage point estimate.

    The interval width is driven by a combined confidence measure that blends
    signal-agreement confidence (70 % weight) and data quality (30 % weight).

    Args:
        point_estimate_pct: The point estimate in [0, 100] percentage space.
        confidence_level:   Signal-agreement confidence in [0, 1], from
                            FileAnalysis.confidence.
        data_quality:       Data quality score in [0, 1]. Reflects how many
                            analysis layers were active (AST, git, …).

    Returns:
        ConfidenceInterval with ``low`` and ``high`` clamped to [0, 100].
    """
    confidence_level = max(0.0, min(1.0, confidence_level))
    data_quality = max(0.0, min(1.0, data_quality))

    combined = confidence_level * 0.7 + data_quality * 0.3

    if combined > 0.70:
        half_width = 6.0
    elif combined > 0.50:
        half_width = 12.0
    else:
        half_width = 22.0

    low = max(0.0, point_estimate_pct - half_width)
    high = min(100.0, point_estimate_pct + half_width)
    return ConfidenceInterval(low=low, high=high)


def portfolio_interval(
    point_estimate_pct: float,
    n_repos: int,
    avg_confidence: float,
) -> ConfidenceInterval:
    """
    Compute a portfolio-level confidence interval for an aggregated origin estimate.

    More repositories narrow the interval (law of large numbers analogue for
    heuristic estimates). Interval width is clamped to a minimum of 3 pp and a
    maximum of 25 pp on each side.

    Args:
        point_estimate_pct: Aggregated percentage point estimate in [0, 100].
        n_repos:            Number of repositories contributing to the estimate.
                            Must be >= 1.
        avg_confidence:     Average file-level confidence across the portfolio,
                            in [0, 1].

    Returns:
        ConfidenceInterval with ``low`` and ``high`` clamped to [0, 100].
    """
    avg_confidence = max(0.0, min(1.0, avg_confidence))
    n_repos = max(1, n_repos)

    base_width = 22.0 * (1.0 - avg_confidence)
    repo_factor = max(0.4, 1.0 / (n_repos ** 0.5))
    half_width = base_width * repo_factor

    # Clamp half-width to [3, 25]
    half_width = max(3.0, min(25.0, half_width))

    low = max(0.0, point_estimate_pct - half_width)
    high = min(100.0, point_estimate_pct + half_width)
    return ConfidenceInterval(low=low, high=high)
