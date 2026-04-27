"""
domain.py — Core domain objects for the Code Engineering Pattern Analyzer v5.0.

Defines the primary domain concepts used throughout the pipeline:
  - FileCategory (semantic file classification)
  - FileContext (per-file analysis context)
  - Finding / Evidence / AlternativeExplanation (explainable results)
  - ScoreBreakdown (raw vs adjusted scoring)
  - FrameworkContext (detected framework boilerplate)
  - OriginEstimate (three-way AI/human probability distribution) [v5.0]
  - ScanConfig (configuration for a scan run)

Design principles:
  - All objects are JSON-serializable via as_dict()
  - Immutable after construction where practical (frozen dataclasses)
  - Typed with explicit fields; no dynamic attribute injection
  - Every finding carries evidence and alternative explanations
  - No AI-authorship claims; only pattern signals

⚠ DISCLAIMER: Scores are pattern indicators, NOT proof of AI origin.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .origin.confidence import ConfidenceInterval  # noqa: F401 (re-exported)


# ── File category ──────────────────────────────────────────────────────────────

class FileCategory(str, Enum):
    """
    Semantic category of a source file, determined before scoring.
    Category affects score interpretation, adjusted score, and risk.
    """
    PRODUCTION_LOGIC  = "production_logic"    # core domain / business logic
    DTO_MAPPER        = "dto_mapper"           # data transfer objects, mappers
    TEST              = "test"                 # test files
    GENERATED         = "generated"            # auto-generated code
    CONFIG_INFRA      = "config_infra"         # configuration, build, infra
    MIGRATION         = "migration"            # DB migration / upgrade scripts
    EXAMPLE           = "example"              # examples, tutorials, demos
    NOTEBOOK          = "notebook"             # Jupyter notebooks
    VENDOR            = "vendor"               # vendored third-party code
    BOILERPLATE_INTEG = "boilerplate_integ"    # framework integration boilerplate
    UNKNOWN           = "unknown"              # classification not possible

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def prior_ai_score(self) -> float:
        """
        Bayesian prior for AI-like signal probability by category.
        Generated, DTO, and framework boilerplate naturally look AI-like.
        These priors soften interpretation, not override it.
        """
        return _CATEGORY_PRIORS.get(self, 0.40)

    @property
    def adjustment_factor(self) -> float:
        """
        Multiplicative factor applied to raw score for adjusted score.
        Categories that are inherently regular get a downward adjustment.
        """
        return _CATEGORY_ADJUSTMENTS.get(self, 1.0)


_CATEGORY_PRIORS: Dict[FileCategory, float] = {
    FileCategory.PRODUCTION_LOGIC:  0.35,
    FileCategory.DTO_MAPPER:        0.70,  # DTOs naturally look AI-like
    FileCategory.TEST:              0.45,
    FileCategory.GENERATED:         0.90,  # generated code is very AI-like by nature
    FileCategory.CONFIG_INFRA:      0.55,
    FileCategory.MIGRATION:         0.60,
    FileCategory.EXAMPLE:           0.65,
    FileCategory.NOTEBOOK:          0.40,
    FileCategory.VENDOR:            0.50,
    FileCategory.BOILERPLATE_INTEG: 0.65,
    FileCategory.UNKNOWN:           0.40,
}

_CATEGORY_ADJUSTMENTS: Dict[FileCategory, float] = {
    FileCategory.PRODUCTION_LOGIC:  1.00,   # no adjustment — this is what we care about
    FileCategory.DTO_MAPPER:        0.60,   # DTOs are inherently regular; reduce score
    FileCategory.TEST:              0.80,   # tests have some AI signals naturally
    FileCategory.GENERATED:         0.20,   # generated code excluded from KPI
    FileCategory.CONFIG_INFRA:      0.70,   # config is usually structured
    FileCategory.MIGRATION:         0.65,   # migrations are formulaic
    FileCategory.EXAMPLE:           0.60,   # examples are typically clean/formal
    FileCategory.NOTEBOOK:          0.75,
    FileCategory.VENDOR:            0.10,   # vendor code excluded from KPI
    FileCategory.BOILERPLATE_INTEG: 0.55,
    FileCategory.UNKNOWN:           0.90,
}


# ── Evidence ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Evidence:
    """A concrete piece of evidence supporting a finding."""
    kind: str           # "pattern" | "snippet" | "statistic" | "structural"
    description: str
    value: Optional[float] = None    # numeric evidence value
    snippet: Optional[str] = None    # code snippet (None in safe mode)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind":        self.kind,
            "description": self.description,
            "value":       round(self.value, 4) if self.value is not None else None,
            "snippet":     self.snippet,
        }


# ── Alternative explanation ────────────────────────────────────────────────────

@dataclass(frozen=True)
class AlternativeExplanation:
    """
    A plausible non-AI explanation for an elevated signal.
    Every finding should carry at least one alternative explanation
    to prevent over-interpretation of results.
    """
    explanation: str
    likelihood: str  # "high" | "moderate" | "low"

    def as_dict(self) -> Dict[str, Any]:
        return {"explanation": self.explanation, "likelihood": self.likelihood}


# ── Finding ────────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    """
    A single analyzable pattern finding with full explainability.

    Findings are the primary evidence layer. Each finding:
      - names a specific rule that triggered
      - shows score contribution
      - provides evidence (what was found)
      - provides alternative explanations (why it might NOT be AI)
    """
    rule_id: str
    category: str           # "lexical" | "structural" | "heuristic" | "git" | "framework" | "test"
    description: str
    score_contribution: float        # contribution to raw score [0.0, 1.0]
    confidence: float                # signal confidence [0.0, 1.0]
    severity: str                    # "info" | "low" | "moderate" | "high"
    evidence: List[Evidence] = field(default_factory=list)
    alternative_explanations: List[AlternativeExplanation] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":               self.rule_id,
            "category":              self.category,
            "description":           self.description,
            "score_contribution":    round(self.score_contribution, 4),
            "confidence":            round(self.confidence, 4),
            "severity":              self.severity,
            "evidence":              [e.as_dict() for e in self.evidence],
            "alternative_explanations": [ae.as_dict() for ae in self.alternative_explanations],
            "tags":                  self.tags,
        }

    @property
    def severity_rank(self) -> int:
        return {"info": 0, "low": 1, "moderate": 2, "high": 3}.get(self.severity, 0)


# ── Score breakdown ────────────────────────────────────────────────────────────

@dataclass
class ScoreBreakdown:
    """
    Detailed scoring breakdown separating raw from adjusted scores.

    raw_score:          Purely heuristic signal aggregate [0.0, 1.0]
    adjusted_score:     Raw score after category/framework context adjustments
    category_adj:       How much category context shifted the score (negative = reduced)
    framework_adj:      How much framework context shifted the score
    confidence:         Signal agreement fraction [0.0, 1.0]
    risk_score:         Combined engineering risk signal (≠ AI-likeness)
    uncertainty_reasons: Human-readable reasons for reduced confidence
    """
    raw_score: float
    adjusted_score: float
    category_adj: float
    framework_adj: float
    confidence: float
    risk_score: float
    uncertainty_reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "raw_score":           round(self.raw_score, 4),
            "adjusted_score":      round(self.adjusted_score, 4),
            "category_adj":        round(self.category_adj, 4),
            "framework_adj":       round(self.framework_adj, 4),
            "confidence":          round(self.confidence, 4),
            "risk_score":          round(self.risk_score, 4),
            "uncertainty_reasons": self.uncertainty_reasons,
        }


# ── Origin estimate ────────────────────────────────────────────────────────────

@dataclass
class OriginEstimate:
    """
    Three-way heuristic origin pattern estimate for a file or repository.

    Expresses the estimated distribution of code across three pattern categories
    based on code style, structure, git history, and other signals:

      - fully_ai_generated_pct:
          Proportion exhibiting patterns consistent with full AI/scaffold generation:
          high structural homogeneity, prompt residue, no human-history continuity.
          Does NOT mean the code was proven to be LLM-generated.

      - ai_assisted_pct:
          Proportion exhibiting patterns consistent with AI-assisted development:
          localized style discontinuities, partial AI-like sections mixed with
          human-authored context, Copilot-like incremental signals.
          Does NOT mean the code was proven to be written with an AI assistant.

      - human_authored_pct:
          Proportion exhibiting patterns consistent with human-authored code:
          organic irregularity, legacy idioms, gradual history, domain vocabulary.
          Does NOT mean the code was proven to be written without AI tools.

    ⚠ CRITICAL LIMITATIONS:
      - These are directional pattern estimates, NOT forensic proof of authorship.
      - All three categories are computed from heuristics that have known false
        positive and false negative rates.
      - Clean senior code, strict formatters, DTOs, and framework boilerplate
        will appear AI-like regardless of actual origin.
      - AI code that was heavily edited by humans will appear human-like.
      - Generated files (protobuf, OpenAPI, jOOQ) are excluded and must not
        be confused with "LLM-generated" code.
      - These percentages must not be used for individual developer evaluation,
        disciplinary action, or contractual claims.

    The three percentages always sum to approximately 100%.
    """

    fully_ai_generated_pct: float    # 0-100  (AI-pattern signal, not proven origin)
    ai_assisted_pct: float           # 0-100  (AI-pattern signal, not proven origin)
    human_authored_pct: float        # 0-100  (human-pattern signal, not proven origin)
    # Must sum to ~100

    confidence: str           # "low" | "medium" | "high"
    confidence_level: float   # 0-1

    intervals: Dict[str, Any] = field(default_factory=dict)  # key -> ConfidenceInterval
    drivers: List[str] = field(default_factory=list)
    uncertainty_reasons: List[str] = field(default_factory=list)
    methodology: str = "heuristic_pattern_analysis_v5"
    caveats: List[str] = field(default_factory=lambda: [
        "These are heuristic pattern estimates, not forensic proof of AI authorship.",
        "High fully-AI-pattern signal may reflect clean code, strict formatters, "
        "framework boilerplate, DTOs, or generated clients — not LLM generation.",
        "Low scores do not rule out AI-assisted development.",
        "Generated files (proto, OpenAPI, jOOQ) are excluded from this estimate.",
        "Must not be used for individual developer evaluation or disciplinary action.",
    ])

    def validate(self) -> None:
        """Assert that the three percentages sum to approximately 100."""
        total = self.fully_ai_generated_pct + self.ai_assisted_pct + self.human_authored_pct
        assert abs(total - 100.0) < 0.5, f"Origin percentages must sum to 100, got {total}"

    def as_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            # ⚠ These percentages are PATTERN SIGNAL estimates, not authorship proof.
            # See 'caveats' field for full limitations.
            "fully_ai_generated_pct": round(self.fully_ai_generated_pct, 1),
            "ai_assisted_pct": round(self.ai_assisted_pct, 1),
            "human_authored_pct": round(self.human_authored_pct, 1),
            "pct_note": (
                "These percentages reflect heuristic code-pattern signals. "
                "They do not constitute proof of actual authorship or AI tool usage."
            ),
            "confidence": self.confidence,
            "confidence_level": round(self.confidence_level, 3),
            "confidence_interval": {
                k: v.as_dict() if hasattr(v, "as_dict") else v
                for k, v in self.intervals.items()
            },
            "drivers": self.drivers,
            "uncertainty_reasons": self.uncertainty_reasons,
            "methodology": self.methodology,
            "caveats": self.caveats,
        }


# ── Framework context ──────────────────────────────────────────────────────────

@dataclass
class FrameworkContext:
    """
    Detected framework and boilerplate context for a file.

    Framework context is used to interpret AI-like signals correctly.
    A Spring @RestController is expected to look structured and regular
    — that is a framework requirement, not necessarily AI generation.
    """
    detected_frameworks: List[str] = field(default_factory=list)
    is_spring_component: bool = False
    is_jpa_entity: bool = False
    is_lombok_heavy: bool = False
    is_pydantic_model: bool = False
    is_fastapi_route: bool = False
    is_django_model: bool = False
    is_mapstruct_mapper: bool = False
    is_openapi_generated: bool = False
    is_dto_class: bool = False
    boilerplate_score: float = 0.0   # [0, 1] fraction that is pure boilerplate

    def as_dict(self) -> Dict[str, Any]:
        return {
            "detected_frameworks":  self.detected_frameworks,
            "is_spring_component":  self.is_spring_component,
            "is_jpa_entity":        self.is_jpa_entity,
            "is_lombok_heavy":      self.is_lombok_heavy,
            "is_pydantic_model":    self.is_pydantic_model,
            "is_fastapi_route":     self.is_fastapi_route,
            "is_django_model":      self.is_django_model,
            "is_mapstruct_mapper":  self.is_mapstruct_mapper,
            "is_openapi_generated": self.is_openapi_generated,
            "is_dto_class":         self.is_dto_class,
            "boilerplate_score":    round(self.boilerplate_score, 4),
        }

    @property
    def is_framework_boilerplate(self) -> bool:
        return (self.boilerplate_score > 0.5 or self.is_mapstruct_mapper
                or self.is_openapi_generated or self.is_dto_class)


# ── Scan config ────────────────────────────────────────────────────────────────

@dataclass
class ScanConfig:
    """
    Configuration for a single scan run. Loaded from file or CLI flags.

    Extension point: additional adapters can be wired by adding fields here
    and implementing corresponding adapters in the integration layer.
    """
    # Versioning
    scoring_model_version: str = "5.0"
    ruleset_version: str = "5.0"

    # Feature flags
    enable_ast: bool = False
    enable_entropy: bool = False
    enable_similarity: bool = False
    enable_git: bool = False
    enable_framework_detection: bool = True
    enable_placeholder_detection: bool = True
    enable_test_quality: bool = True

    # Scan settings
    workers: int = 1
    include_tests: bool = True
    exclude_tests: bool = False

    # Output settings
    output_format: str = "table"    # table | json | markdown | csv | sarif
    include_snippets: bool = False
    use_color: bool = True
    quiet: bool = False

    # Scan profile
    profile: str = "default"

    # Paths and filters
    ignored_paths: List[str] = field(default_factory=list)
    critical_paths: List[str] = field(default_factory=list)
    generated_paths: List[str] = field(default_factory=list)
    dirs: List[str] = field(default_factory=list)

    # Thresholds
    ai_thresh_high: float = 0.68
    ai_thresh_low: float = 0.62
    min_confidence: float = 0.45
    fail_on_high_risk: bool = False

    # Domain vocabulary (for domain specificity scoring)
    domain_terms: List[str] = field(default_factory=list)

    # Privacy mode
    privacy_mode: str = "local"   # local | safe | hash

    # Policy
    fail_on_policy: bool = False

    # Suppressions (rule_id → reason)
    suppressions: Dict[str, str] = field(default_factory=dict)

    # Ruleset groups
    ruleset_groups: List[str] = field(default_factory=lambda: ["default"])

    # CI mode
    ci_mode: bool = False
    changed_only: bool = False
    baseline_file: Optional[str] = None

    # Debug
    debug_rules: bool = False
    profile_performance: bool = False

    # Author-level analysis (disabled by default — anti-misuse guardrail)
    enable_author_analysis: bool = False

    # v5.0: KPI inclusion controls
    include_vendor_in_kpi: bool = False
    include_generated_in_kpi: bool = False
    show_vendor_summary: bool = True
    show_generated_summary: bool = True

    # v5.0: Temporal analysis window
    historical_baseline_cutoff: str = "2022-01-01"
    recent_code_window_months: int = 12

    # v5.0: Developer fingerprint (disabled by default — ethics guardrail)
    developer_fingerprint_enabled: bool = False

    @classmethod
    def from_profile(cls, profile: str, **overrides: Any) -> "ScanConfig":
        """Create a ScanConfig from a named scan profile."""
        cfg = cls(profile=profile)

        if profile == "quick":
            cfg.enable_ast = False
            cfg.enable_entropy = False
            cfg.enable_similarity = False
            cfg.enable_git = False
            cfg.enable_framework_detection = True
            cfg.enable_placeholder_detection = True

        elif profile == "ci":
            cfg.enable_ast = True
            cfg.enable_entropy = True
            cfg.enable_similarity = False
            cfg.enable_git = True
            cfg.ci_mode = True

        elif profile == "full":
            cfg.enable_ast = True
            cfg.enable_entropy = True
            cfg.enable_similarity = True
            cfg.enable_git = True

        elif profile == "forensic":
            cfg.enable_ast = True
            cfg.enable_entropy = True
            cfg.enable_similarity = True
            cfg.enable_git = True
            cfg.include_snippets = True
            cfg.output_format = "json"

        elif profile == "leadership":
            cfg.enable_ast = True
            cfg.enable_entropy = True
            cfg.enable_git = True
            cfg.output_format = "markdown"

        elif profile == "calibration":
            cfg.enable_ast = True
            cfg.enable_entropy = True
            cfg.enable_similarity = True
            cfg.enable_git = True
            cfg.debug_rules = True
            cfg.profile_performance = True

        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)

        return cfg


# ── Maturity level ─────────────────────────────────────────────────────────────

class MaturityLevel(str, Enum):
    """
    Analyzer maturity level for a file scan.
    Reflects which analysis layers were available.
    """
    LEXICAL_ONLY    = "lexical_only"
    AST_AWARE       = "ast_aware"
    CONTEXT_AWARE   = "context_aware"
    HISTORY_AWARE   = "history_aware"
    GOVERNANCE_READY = "governance_ready"


def get_maturity_level(
    has_ast: bool,
    has_git: bool,
    has_framework: bool,
    has_baseline: bool,
) -> MaturityLevel:
    if has_ast and has_git and has_framework and has_baseline:
        return MaturityLevel.GOVERNANCE_READY
    if has_ast and has_git and has_framework:
        return MaturityLevel.HISTORY_AWARE
    if has_ast and has_framework:
        return MaturityLevel.CONTEXT_AWARE
    if has_ast:
        return MaturityLevel.AST_AWARE
    return MaturityLevel.LEXICAL_ONLY


# ── Score band ─────────────────────────────────────────────────────────────────

def score_band(score: float) -> str:
    """Return a human-readable score band from an adjusted 0–100 score."""
    if score < 25:
        return "low"
    if score < 50:
        return "moderate"
    if score < 75:
        return "elevated"
    return "high"


def score_band_from_likelihood(likelihood: float) -> str:
    return score_band(likelihood * 100)


# ── Review recommendation ──────────────────────────────────────────────────────

def review_recommendation(
    adjusted_score: float,
    risk_score: float,
    category: FileCategory,
    confidence: float,
) -> str:
    """
    Generate a review recommendation based on scores and context.
    Returns: "no_action" | "review_as_boilerplate" | "review_ai_scaffold" | "manual_review"
    """
    if category in (FileCategory.GENERATED, FileCategory.VENDOR):
        return "no_action"
    if adjusted_score < 0.30 or confidence < 0.35:
        return "no_action"
    if category in (FileCategory.DTO_MAPPER, FileCategory.CONFIG_INFRA,
                    FileCategory.BOILERPLATE_INTEG):
        if adjusted_score < 0.55:
            return "review_as_boilerplate"
    if risk_score >= 0.65:
        return "manual_review"
    if adjusted_score >= 0.62:
        return "review_ai_scaffold"
    if adjusted_score >= 0.40:
        return "review_as_boilerplate"
    return "no_action"
