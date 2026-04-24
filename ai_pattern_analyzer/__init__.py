"""
ai_pattern_analyzer — Code Generation Pattern Analyzer v3.0

Detects AI-like coding patterns using:
  • Heuristic analysis (17 signals, language-specific weights)
  • AST-based structural analysis (Python)
  • Lexical entropy and type-token ratio
  • Cross-file TF-IDF cosine similarity
  • Git commit metadata analysis

⚠ DISCLAIMER: This tool detects statistical patterns in code style.
It does NOT prove AI authorship, does NOT identify code origin,
and MUST NOT be used as evidence for personnel or policy decisions.
Results are probabilistic trend indicators only.

Run:  python -m ai_pattern_analyzer --dirs ./repo --help
"""

__version__ = "3.0.0"
__author__  = "GPC Platform Team"
