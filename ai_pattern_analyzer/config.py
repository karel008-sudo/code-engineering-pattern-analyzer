"""
config.py — Language definitions, weights, and system-wide constants.

All signal weights sum to 1.0 per language.
Signal values are normalized to [0.0, 1.0] where 1.0 = AI-like pattern.

v4.0: Added scoring model version, ruleset version, extended signal keys,
      new heuristic signals (placeholder, test_quality, framework signals).

v5.0: Added Kotlin-native signal keys, scaffold/style signals, WEIGHTS_KOTLIN,
      GIT_BURST_HUMAN_KEYWORDS, updated versioning. Added .kts extension.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, FrozenSet

# ── Analyzer versioning ────────────────────────────────────────────────────────

ANALYZER_VERSION       = "5.0.0"
SCORING_MODEL_VERSION  = "5.0"
RULESET_VERSION        = "5.0"

# ── File filtering ────────────────────────────────────────────────────────────

SKIP_DIRS: frozenset = frozenset({
    "node_modules", "target", "build", "dist", ".git", "__pycache__",
    ".venv", "venv", ".gradle", "generated", "coverage", ".mvn",
    "vendor", "third_party", "thirdparty", ".idea", ".vscode",
    ".pytest_cache", ".mypy_cache", "site-packages", "dist-packages",
    # v5.0 additions
    "proto", "grpc", "avro", "swagger", "openapi",
    "Pods", "Carthage", "deps",
})

MAX_FILE_BYTES: int = 512 * 1024
MIN_LINES: int = 10

# ── Language mapping ──────────────────────────────────────────────────────────

EXTENSION_TO_LANG: Dict[str, str] = {
    ".java":  "Java",   ".kt":    "Kotlin",  ".kts":   "KotlinScript",
    ".scala": "Scala",
    ".py":    "Python", ".ts":    "TypeScript", ".tsx":   "TypeScript",
    ".vue":   "Vue",    ".js":    "JavaScript", ".jsx":   "JavaScript",
    ".go":    "Go",     ".rs":    "Rust",    ".cs":    "CSharp",
    ".cpp":   "CPP",    ".cc":    "CPP",     ".c":     "C",
    ".rb":    "Ruby",   ".php":   "PHP",     ".swift": "Swift",
    ".scss":  "SCSS",   ".css":   "CSS",     ".sql":   "SQL",
}

SUPPORTED_LANGS: frozenset = frozenset({
    "Python", "Java", "Kotlin", "TypeScript", "JavaScript", "Vue",
})

# ── Signal keys ───────────────────────────────────────────────────────────────
# All signals normalized to [0.0, 1.0] where 1.0 = strong AI-like pattern.

ALL_SIGNAL_KEYS = [
    # Lexical signals (--entropy flag)
    "token_entropy",           # low entropy = repetitive = AI-like
    "type_token_ratio",        # low TTR (few unique tokens) = AI-like
    "repetition_index",        # structural block repetition = AI-like
    # Heuristic signals (always active)
    "comment_density",         # over-commenting = AI-like
    "docstring_quality",       # structured Args:/Returns: blocks = AI-like
    "type_annotations",        # full type coverage (Python) = AI-like
    "exception_style",         # specific exceptions + reraise = AI-like
    "error_message_quality",   # rich contextual error strings = AI-like
    "log_quality",             # parameterized log calls = AI-like
    "function_name_length",    # long descriptive names = AI-like
    # Java-specific heuristics
    "stream_usage",            # Stream API > loops = AI-like
    "empty_catch",             # absence of empty catch = AI-like
    "final_fields",            # private final fields = AI-like
    "optional_usage",          # Optional<T> usage = AI-like
    "lombok_annotations",      # annotation-driven design = AI-like
    # AST-based structural signals (--ast flag)
    "ast_depth_uniformity",    # uniform nesting = AI-like
    "ast_type_diversity",      # low node-type diversity = AI-like
    "ast_avg_func_length",     # short focused functions = AI-like
    # v4.0: Placeholder / LLM residue signals
    "placeholder_density",     # TODO/FIXME/placeholder/dummy literals = caution
    "prompt_residue",          # "Here is", "You can use", "replace with" = AI hint
    # v4.0: Test quality signals (for test files)
    "test_assertion_quality",  # shallow assertions = AI-like test
    "test_mock_abuse",         # excessive mocking = AI-like test
    "test_fixture_realism",    # generic fixtures = AI-like test
    # v4.0: Framework / structural motifs
    "motif_uniformity",        # low structural motif diversity = AI-like
    "intra_file_variance",     # uniform methods across file = AI-like
    # Repo-level (injected after cross-file analysis)
    "similarity_cluster",      # high cross-file similarity = AI-like
    # v5.0: Scaffold / structural coherence signals
    "scaffold_completeness",   # uniform scaffold structure = AI-like
    "magic_number_discipline", # low magic numbers = AI-like (or senior dev)
    "name_body_coherence",     # names match body = AI-like descriptive naming
    "style_continuity",        # continuous style = slightly AI-like
    "human_irregularity",      # human patterns = human signal (inverted: 1 - value)
    # v5.0: Kotlin-native signals (LOW AI weights — idiomatic Kotlin)
    "kotlin_data_class",       # Kotlin data classes = LOW AI signal (idiomatic)
    "kotlin_coroutines",       # Kotlin coroutines = contextual signal
]


# ── Per-language weight tables ────────────────────────────────────────────────

@dataclass
class LanguageWeights:
    lang: str
    weights: Dict[str, float]

    def __post_init__(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-5:
            raise ValueError(f"{self.lang} weights sum to {total:.4f}, not 1.0")

    def get(self, key: str, default: float = 0.0) -> float:
        return self.weights.get(key, default)

    def items(self):
        return self.weights.items()


def _w(**kw) -> Dict[str, float]:
    """Fill missing signal keys with 0.0."""
    d = {k: 0.0 for k in ALL_SIGNAL_KEYS}
    d.update(kw)
    return d


WEIGHTS_PYTHON = LanguageWeights("Python", _w(
    # Data-verified: Δ > 30 (AI avg vs human avg separation)
    type_annotations      = 0.16,
    comment_density       = 0.11,
    docstring_quality     = 0.10,
    # Δ 10–30
    token_entropy         = 0.07,
    exception_style       = 0.07,
    error_message_quality = 0.06,
    type_token_ratio      = 0.05,
    function_name_length  = 0.05,
    # AST-based
    ast_type_diversity    = 0.05,
    ast_avg_func_length   = 0.04,
    ast_depth_uniformity  = 0.03,
    # Weak but present
    log_quality           = 0.03,
    repetition_index      = 0.03,
    similarity_cluster    = 0.03,
    # v4.0 signals
    motif_uniformity      = 0.04,
    intra_file_variance   = 0.03,
    prompt_residue        = 0.02,
    placeholder_density   = 0.02,
    # padding to sum to 1.0
    test_assertion_quality = 0.01,
))

WEIGHTS_JAVA = LanguageWeights("Java", _w(
    # Data-verified: Δ > 30
    docstring_quality     = 0.14,
    stream_usage          = 0.13,
    comment_density       = 0.11,
    log_quality           = 0.09,
    error_message_quality = 0.07,
    # Δ 10–30
    token_entropy         = 0.06,
    optional_usage        = 0.06,
    lombok_annotations    = 0.06,
    empty_catch           = 0.06,
    similarity_cluster    = 0.04,
    # Weak
    final_fields          = 0.03,
    type_token_ratio      = 0.03,
    repetition_index      = 0.02,
    function_name_length  = 0.01,
    # v4.0 signals
    motif_uniformity      = 0.04,
    intra_file_variance   = 0.03,
    prompt_residue        = 0.01,
    placeholder_density   = 0.01,
))

WEIGHTS_TYPESCRIPT = LanguageWeights("TypeScript", _w(
    type_annotations      = 0.18,
    docstring_quality     = 0.13,
    comment_density       = 0.12,
    token_entropy         = 0.09,
    function_name_length  = 0.09,
    error_message_quality = 0.07,
    type_token_ratio      = 0.06,
    similarity_cluster    = 0.06,
    log_quality           = 0.05,
    repetition_index      = 0.03,
    exception_style       = 0.02,
    motif_uniformity      = 0.04,
    intra_file_variance   = 0.03,
    prompt_residue        = 0.02,
    placeholder_density   = 0.01,
))

WEIGHTS_DEFAULT = LanguageWeights("default", _w(
    comment_density       = 0.18,
    docstring_quality     = 0.16,
    token_entropy         = 0.13,
    type_annotations      = 0.11,
    function_name_length  = 0.09,
    error_message_quality = 0.08,
    type_token_ratio      = 0.07,
    log_quality           = 0.06,
    repetition_index      = 0.04,
    motif_uniformity      = 0.04,
    intra_file_variance   = 0.03,
    prompt_residue        = 0.01,
))

# ── Kotlin-specific weights (v5.0) ─────────────────────────────────────────────
# Key decisions:
#   - kotlin_data_class weight = 0.01 (idiomatic, NOT an AI indicator)
#   - kotlin_coroutines weight = 0.01 (contextual, not decisive)
#   - Adapted from WEIGHTS_JAVA but tuned for Kotlin idioms
#   - Total must sum to 1.0

WEIGHTS_KOTLIN = LanguageWeights("Kotlin", _w(
    # Primary signals — same as Java (strongest separators)
    docstring_quality     = 0.13,
    stream_usage          = 0.11,
    comment_density       = 0.11,
    log_quality           = 0.09,
    error_message_quality = 0.07,
    # Secondary signals
    token_entropy         = 0.06,
    optional_usage        = 0.05,
    empty_catch           = 0.05,
    similarity_cluster    = 0.04,
    # Weak signals
    final_fields          = 0.03,
    type_token_ratio      = 0.03,
    repetition_index      = 0.02,
    function_name_length  = 0.01,
    # v4.0 signals
    motif_uniformity      = 0.04,
    intra_file_variance   = 0.03,
    prompt_residue        = 0.01,
    placeholder_density   = 0.01,
    # v5.0 scaffold signals (moderate weight — supporting evidence)
    scaffold_completeness   = 0.04,
    magic_number_discipline = 0.02,
    name_body_coherence     = 0.02,
    style_continuity        = 0.01,
    # v5.0 Kotlin-native signals — VERY LOW weights (idiomatic constructs)
    kotlin_data_class  = 0.01,   # idiomatic Kotlin — do NOT penalise
    kotlin_coroutines  = 0.01,   # contextual — not decisive
))

LANG_WEIGHTS: Dict[str, LanguageWeights] = {
    "Python":       WEIGHTS_PYTHON,
    "Java":         WEIGHTS_JAVA,
    "Kotlin":       WEIGHTS_KOTLIN,
    "KotlinScript": WEIGHTS_KOTLIN,
    "Scala":        WEIGHTS_JAVA,
    "TypeScript":   WEIGHTS_TYPESCRIPT,
    "Vue":          WEIGHTS_TYPESCRIPT,
    "JavaScript":   WEIGHTS_TYPESCRIPT,
}


def get_weights(lang: str) -> LanguageWeights:
    return LANG_WEIGHTS.get(lang, WEIGHTS_DEFAULT)


# ── Git burst human keywords (v5.0) ───────────────────────────────────────────
# Commit messages containing these keywords often indicate human-driven operations:
# bulk imports, migrations, reformatting, vendor syncs, and cherry-picks.
# These are used to down-weight AI-like signals in files that were recently
# touched by a "human-pattern" commit.

GIT_BURST_HUMAN_KEYWORDS: FrozenSet[str] = frozenset({
    "initial import", "cvs", "svn", "migrate", "migration",
    "move", "rename", "refactor", "reformat", "format",
    "cleanup", "generated", "regenerate", "vendored",
    "import source", "sync", "mirror", "cherry-pick", "squash",
})
