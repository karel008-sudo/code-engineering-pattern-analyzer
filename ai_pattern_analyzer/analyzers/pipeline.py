"""
analyzers/pipeline.py — Top-level importable worker function for multiprocessing.

Must be a module-level function (not nested in __main__) so it can be
pickled by multiprocessing.Pool on macOS/Windows (spawn start method).
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import lexical, structural, heuristics
from ..scoring.model import FileAnalysis, score_file


def analyze_file(args: Tuple) -> Optional[FileAnalysis]:
    """
    Analyze a single file. Called by multiprocessing.Pool.map().
    Returns None if the file cannot be read.
    """
    path_str, language, kind_name, enable_ast, enable_entropy = args
    path = Path(path_str)

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    lines = text.count("\n") + 1
    signals: Dict[str, float] = {}

    # Heuristic signals (always enabled)
    signals.update(heuristics.compute_all(text, language))

    # AST structural analysis (Python only for now)
    if enable_ast:
        signals.update(structural.analyze_structure(text, language))

    # Lexical entropy signals
    if enable_entropy:
        signals["token_entropy"]    = lexical.token_entropy(text)
        signals["type_token_ratio"] = lexical.type_token_ratio(text)
        signals["repetition_index"] = lexical.repetition_index(text)

    return score_file(
        path=path, language=language, kind=kind_name,
        lines=lines, signals=signals,
    )
