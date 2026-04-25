"""
analyzers/pipeline.py — Top-level importable worker function for multiprocessing.

Must be a module-level function (not nested in __main__) so it can be
pickled by multiprocessing.Pool on macOS/Windows (spawn start method).

v4.0: Extended with framework detection, placeholder detection, test quality,
      and structural motif analysis. Worker args tuple extended with category.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import lexical, structural, heuristics
from .framework import detect_framework_context
from .placeholder import compute_placeholder_signals
from .test_quality import compute_test_quality_signals
from ..scoring.model import FileAnalysis, score_file
from ..domain import FileCategory


def _compute_motif_signals(text: str, lang: str) -> Dict[str, float]:
    """
    Compute structural motif signals: motif_uniformity and intra_file_variance.
    Detects repeated code patterns and uniform method structures.
    """
    import re
    import statistics

    # Extract method/function lines for analysis
    if lang == "Python":
        func_pattern = re.compile(r"^\s*(?:async\s+)?def\s+\w+\s*\(", re.M)
    elif lang in ("Java", "Kotlin", "Scala"):
        func_pattern = re.compile(
            r"^\s*(?:public|private|protected|static)\s+\S+\s+\w+\s*\(", re.M
        )
    else:
        func_pattern = re.compile(
            r"^\s*(?:function|func|def|async\s+function)\s+\w+\s*\(", re.M
        )

    func_starts = [m.start() for m in func_pattern.finditer(text)]
    if len(func_starts) < 3:
        return {"motif_uniformity": 0.35, "intra_file_variance": 0.35}

    # Estimate function lengths from start positions
    lengths = []
    for i, start in enumerate(func_starts):
        end = func_starts[i + 1] if i + 1 < len(func_starts) else len(text)
        lengths.append(text[start:end].count("\n"))

    if len(lengths) < 3:
        return {"motif_uniformity": 0.35, "intra_file_variance": 0.35}

    try:
        mean = statistics.mean(lengths)
        stdev = statistics.stdev(lengths)
        cv = stdev / max(mean, 1)
    except statistics.StatisticsError:
        cv = 1.0

    # Low CV = very uniform method lengths = AI-like
    intra_variance_signal = max(0.0, min(1.0, 1.0 - cv / 0.8))

    # Motif uniformity: detect repeated structural patterns (3-line shingles in method bodies)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    shingle_size = 3
    shingles = []
    for i in range(len(lines) - shingle_size + 1):
        # Normalize variable names
        shingle = " | ".join(
            re.sub(r"\b[a-z]\w+\b", "V", lines[i + j])[:60] for j in range(shingle_size)
        )
        shingles.append(shingle)

    if shingles:
        total = len(shingles)
        unique = len(set(shingles))
        repetition = 1.0 - (unique / total)
        motif_signal = max(0.0, min(1.0, (repetition - 0.05) / 0.25))
    else:
        motif_signal = 0.35

    return {
        "motif_uniformity":   round(motif_signal, 4),
        "intra_file_variance": round(intra_variance_signal, 4),
    }


def analyze_file(args: Tuple) -> Optional[FileAnalysis]:
    """
    Analyze a single file. Called by multiprocessing.Pool.map().

    Args tuple: (path_str, language, kind_name, category_value,
                 enable_ast, enable_entropy, enable_framework,
                 enable_placeholder, enable_test_quality,
                 is_critical_path, has_git, module_path)

    Returns None if the file cannot be read or is too small.
    """
    (path_str, language, kind_name, category_value,
     enable_ast, enable_entropy, enable_framework,
     enable_placeholder, enable_test_quality,
     is_critical_path, has_git, module_path) = args

    path = Path(path_str)

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    lines = text.count("\n") + 1
    signals: Dict[str, float] = {}

    # Determine category from value
    try:
        category = FileCategory(category_value)
    except ValueError:
        category = FileCategory.UNKNOWN

    # Skip generated and vendor files from full analysis
    if category in (FileCategory.GENERATED, FileCategory.VENDOR):
        return score_file(
            path=path,
            language=language,
            kind=kind_name,
            lines=lines,
            signals={},
            category=category,
            framework_ctx=None,
            is_critical_path=False,
            has_git=has_git,
            module_path=module_path,
        )

    # 1. Heuristic signals (always enabled)
    signals.update(heuristics.compute_all(text, language))

    # 2. AST structural analysis
    if enable_ast:
        signals.update(structural.analyze_structure(text, language))

    # 3. Lexical entropy
    if enable_entropy:
        signals["token_entropy"]    = lexical.token_entropy(text)
        signals["type_token_ratio"] = lexical.type_token_ratio(text)
        signals["repetition_index"] = lexical.repetition_index(text)

    # 4. Framework detection (always when enabled)
    framework_ctx = None
    if enable_framework:
        framework_ctx = detect_framework_context(text, language)

    # 5. Placeholder / LLM residue detection
    if enable_placeholder:
        signals.update(compute_placeholder_signals(text, language))

    # 6. Test quality signals (for test files)
    if enable_test_quality and category == FileCategory.TEST:
        signals.update(compute_test_quality_signals(text, language))

    # 7. Structural motif signals
    signals.update(_compute_motif_signals(text, language))

    return score_file(
        path=path,
        language=language,
        kind=kind_name,
        lines=lines,
        signals=signals,
        category=category,
        framework_ctx=framework_ctx,
        is_critical_path=is_critical_path,
        has_git=has_git,
        module_path=module_path,
    )
