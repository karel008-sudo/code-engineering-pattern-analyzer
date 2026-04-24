"""
analyzers/structural.py — AST-based and structural code analysis.

Python: uses stdlib `ast` for accurate analysis.
Java/others: regex-based approximation.

All functions return floats in [0.0, 1.0] where 1.0 = AI-like pattern.
"""
from __future__ import annotations
import ast
import math
import re
import statistics
from collections import Counter
from typing import Dict, List, Optional, Tuple


# ── Python AST analysis ───────────────────────────────────────────────────────

def _ast_depth(node: ast.AST, depth: int = 0) -> int:
    """Recursively compute maximum AST depth."""
    children = list(ast.iter_child_nodes(node))
    if not children:
        return depth
    return max(_ast_depth(child, depth + 1) for child in children)


def analyze_python_ast(text: str) -> Dict[str, float]:
    """
    Parse Python source with ast and extract structural signals.
    Returns partial dict (only keys that could be computed).
    Empty dict on parse failure.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}

    results: Dict[str, float] = {}

    # ── Node type diversity ────────────────────────────────────────────────
    node_types = Counter(type(n).__name__ for n in ast.walk(tree))
    total_nodes = sum(node_types.values())
    if total_nodes > 0:
        # High diversity = many different node types = human (more irregular)
        # Low diversity = AI tends to use fewer distinct constructs
        diversity = len(node_types) / total_nodes
        # Typical range: 0.05–0.20; normalize to [0,1] and invert for AI signal
        ai_signal = max(0.0, min(1.0, 1.0 - (diversity - 0.02) / 0.18))
        results["ast_type_diversity"] = round(ai_signal, 4)

    # ── Average function length ────────────────────────────────────────────
    func_lengths: List[int] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip dunders — always short regardless of author
            if node.name.startswith("__") and node.name.endswith("__"):
                continue
            if hasattr(node, "end_lineno") and node.end_lineno:
                func_lengths.append(node.end_lineno - node.lineno)

    if func_lengths:
        avg_len = statistics.mean(func_lengths)
        long_ratio = sum(1 for l in func_lengths if l > 50) / len(func_lengths)
        # AI: short functions (avg < 20), few long ones
        # Human: mixed, often has functions > 50 lines
        if long_ratio > 0.30:
            results["ast_avg_func_length"] = 0.10  # many long functions = human
        elif avg_len < 15:
            results["ast_avg_func_length"] = 0.80  # very short = AI
        elif avg_len < 25:
            results["ast_avg_func_length"] = 0.60
        elif avg_len < 40:
            results["ast_avg_func_length"] = 0.40
        else:
            results["ast_avg_func_length"] = 0.20

    # ── Depth uniformity ──────────────────────────────────────────────────
    # Measure depth of each top-level function/class definition
    depths: List[int] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            depths.append(_ast_depth(node))

    if len(depths) >= 3:
        cv = statistics.stdev(depths) / max(statistics.mean(depths), 1)
        # Low CV = uniform depth = AI-like
        ai_signal = max(0.0, min(1.0, 1.0 - cv / 0.6))
        results["ast_depth_uniformity"] = round(ai_signal, 4)

    return results


# ── Java/generic structural approximation ─────────────────────────────────────

def _estimate_function_lengths(text: str, lang: str) -> List[int]:
    """Estimate method lengths by counting lines between { } blocks."""
    if lang == "Python":
        return []  # handled by AST

    lines = text.splitlines()
    lengths: List[int] = []
    depth = 0
    func_start: Optional[int] = None

    method_start_re = re.compile(
        r"(?:public|private|protected|static|async|function|def)\s+"
        r"(?:static\s+)?[\w<>\[\]]+\s+\w+\s*\("
    )

    for i, line in enumerate(lines):
        opens  = line.count("{")
        closes = line.count("}")
        if depth == 0 and opens > 0 and method_start_re.search(line):
            func_start = i
        depth += opens - closes
        if depth <= 0:
            depth = 0
            if func_start is not None:
                lengths.append(i - func_start)
                func_start = None

    return lengths


def analyze_structure(text: str, lang: str) -> Dict[str, float]:
    """
    Structural analysis for non-Python or as fallback.
    Returns partial signal dict.
    """
    results: Dict[str, float] = {}

    if lang == "Python":
        results.update(analyze_python_ast(text))
        return results

    # Function/method length distribution
    lengths = _estimate_function_lengths(text, lang)
    if lengths:
        avg = statistics.mean(lengths)
        long_ratio = sum(1 for l in lengths if l > 60) / len(lengths)
        if long_ratio > 0.30:
            results["ast_avg_func_length"] = 0.10
        elif avg < 20:
            results["ast_avg_func_length"] = 0.75
        elif avg < 35:
            results["ast_avg_func_length"] = 0.55
        elif avg < 50:
            results["ast_avg_func_length"] = 0.35
        else:
            results["ast_avg_func_length"] = 0.18

    return results
