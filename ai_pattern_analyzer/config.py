"""
config.py — Language definitions, weights, and system-wide constants.

All signal weights sum to 1.0 per language.
Signal values are normalized to [0.0, 1.0] where 1.0 = AI-like pattern.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

# ── File filtering ────────────────────────────────────────────────────────────

SKIP_DIRS: frozenset = frozenset({
    "node_modules", "target", "build", "dist", ".git", "__pycache__",
    ".venv", "venv", ".gradle", "generated", "coverage", ".mvn",
    "vendor", "third_party", "thirdparty", ".idea", ".vscode",
    ".pytest_cache", ".mypy_cache", "site-packages", "dist-packages",
})

MAX_FILE_BYTES: int = 512 * 1024
MIN_LINES: int = 10

# ── Language mapping ──────────────────────────────────────────────────────────

EXTENSION_TO_LANG: Dict[str, str] = {
    ".java":  "Java",   ".kt":    "Kotlin",  ".scala": "Scala",
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
    # Lexical signals
    "token_entropy",          # low entropy = repetitive = AI-like
    "type_token_ratio",       # low TTR (few unique tokens) = AI-like
    "repetition_index",       # structural block repetition = AI-like
    # Heuristic signals (code-style)
    "comment_density",        # over-commenting = AI-like
    "docstring_quality",      # structured Args:/Returns: blocks = AI-like
    "type_annotations",       # full type coverage (Python) = AI-like
    "exception_style",        # specific exceptions + reraise = AI-like
    "error_message_quality",  # rich contextual error strings = AI-like
    "log_quality",            # parameterized log calls = AI-like
    "function_name_length",   # long descriptive names = AI-like
    # Java-specific
    "stream_usage",           # Stream API > loops = AI-like
    "empty_catch",            # absence of empty catch = AI-like
    "final_fields",           # private final fields = AI-like
    "optional_usage",         # Optional<T> usage = AI-like
    "lombok_annotations",     # annotation-driven design = AI-like
    # AST-based structural signals
    "ast_depth_uniformity",   # uniform nesting = AI-like
    "ast_type_diversity",     # low node-type diversity = AI-like
    "ast_avg_func_length",    # short focused functions = AI-like
    # Repo-level (injected after cross-file analysis)
    "similarity_cluster",     # high cross-file similarity = AI-like
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
    type_annotations      = 0.18,
    comment_density       = 0.12,
    docstring_quality     = 0.11,
    # Δ 10–30
    token_entropy         = 0.08,
    exception_style       = 0.08,
    error_message_quality = 0.07,
    type_token_ratio      = 0.06,
    function_name_length  = 0.06,
    # AST-based
    ast_type_diversity    = 0.06,
    ast_avg_func_length   = 0.05,
    ast_depth_uniformity  = 0.04,
    # Weak but present
    log_quality           = 0.03,
    repetition_index      = 0.03,
    similarity_cluster    = 0.03,
))

WEIGHTS_JAVA = LanguageWeights("Java", _w(
    # Data-verified: Δ > 30
    docstring_quality     = 0.16,
    stream_usage          = 0.15,
    comment_density       = 0.12,
    log_quality           = 0.10,
    error_message_quality = 0.08,
    # Δ 10–30
    token_entropy         = 0.07,
    optional_usage        = 0.07,
    lombok_annotations    = 0.06,
    empty_catch           = 0.06,
    similarity_cluster    = 0.04,
    # Weak
    final_fields          = 0.03,
    type_token_ratio      = 0.03,
    repetition_index      = 0.02,
    function_name_length  = 0.01,
))

WEIGHTS_TYPESCRIPT = LanguageWeights("TypeScript", _w(
    type_annotations      = 0.20,
    docstring_quality     = 0.15,
    comment_density       = 0.14,
    token_entropy         = 0.10,
    function_name_length  = 0.10,
    error_message_quality = 0.08,
    type_token_ratio      = 0.07,
    similarity_cluster    = 0.06,
    log_quality           = 0.05,
    repetition_index      = 0.03,
    exception_style       = 0.02,
))

WEIGHTS_DEFAULT = LanguageWeights("default", _w(
    comment_density       = 0.20,
    docstring_quality     = 0.18,
    token_entropy         = 0.14,
    type_annotations      = 0.12,
    function_name_length  = 0.10,
    error_message_quality = 0.08,
    type_token_ratio      = 0.08,
    log_quality           = 0.06,
    repetition_index      = 0.04,
))

LANG_WEIGHTS: Dict[str, LanguageWeights] = {
    "Python":     WEIGHTS_PYTHON,
    "Java":       WEIGHTS_JAVA,
    "Kotlin":     WEIGHTS_JAVA,
    "Scala":      WEIGHTS_JAVA,
    "TypeScript": WEIGHTS_TYPESCRIPT,
    "Vue":        WEIGHTS_TYPESCRIPT,
    "JavaScript": WEIGHTS_TYPESCRIPT,
}


def get_weights(lang: str) -> LanguageWeights:
    return LANG_WEIGHTS.get(lang, WEIGHTS_DEFAULT)
