"""
ai_pattern_analyzer — Code Engineering Pattern Analyzer v4.0

Estimates AI-like, automation-like, and generated-code characteristics in
Python and Java repositories using multi-layer heuristic analysis:

  • Heuristic signals (27 signals, language-specific weights)
  • Framework-aware interpretation (Spring, JPA, Pydantic, FastAPI, etc.)
  • File category classification (production logic, DTO, test, generated, etc.)
  • Raw score vs. adjusted score (context-aware interpretation)
  • Confidence model with uncertainty reasons
  • Engineering risk score (separate from AI-likeness)
  • AST-based structural analysis (Python)
  • Lexical entropy and type-token ratio
  • Cross-file TF-IDF cosine similarity
  • Git commit metadata analysis
  • Placeholder and LLM-residue detection
  • Test quality signals (assertion quality, mock abuse, fixture realism)
  • Module-level aggregation and reporting

Output formats: table, JSON, Markdown, CSV, SARIF (stub)
Scan profiles: quick, ci, full, forensic, leadership, calibration

⚠ DISCLAIMER: This tool detects statistical patterns in code style.
It does NOT prove AI authorship, does NOT identify code origin,
and MUST NOT be used as evidence for personnel or policy decisions.
Results are probabilistic trend indicators — directional proxies only.

Run:  python -m ai_pattern_analyzer --dirs ./repo --help
      python -m ai_pattern_analyzer --generate-config
"""

__version__ = "5.0.0"
__author__  = "GPC Platform Team"

from .config import ANALYZER_VERSION, SCORING_MODEL_VERSION, RULESET_VERSION
