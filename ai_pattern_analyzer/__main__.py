"""
__main__.py — CLI entry point. Run as: python -m ai_pattern_analyzer [options]

Usage examples:
  python -m ai_pattern_analyzer --dirs ./my-repo
  python -m ai_pattern_analyzer --dirs ./repo1 ./repo2 --include-git --similarity
  python -m ai_pattern_analyzer --dirs ./repo --exclude-tests --output json > report.json
  python -m ai_pattern_analyzer --dirs ./repo --ast --entropy --output csv > data.csv

⚠ Disclaimer printed at startup. This tool detects patterns, not authorship.
"""
from __future__ import annotations
import argparse
import json
import multiprocessing
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Local imports ──────────────────────────────────────────────────────────────
from .scanners.filesystem import FileKind, walk_repo
from .scanners.git import get_commits
from .analyzers import similarity, git_signals
from .analyzers.pipeline import analyze_file   # top-level importable for multiprocessing
from .scoring.model import FileAnalysis, score_file
from .scoring.calibration import RepoStats, calibrate_repo
from .reporting import cli as cli_reporter, json_report
from .config import EXTENSION_TO_LANG


# ── Argument parsing ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m ai_pattern_analyzer",
        description=(
            "Code Generation Pattern Analyzer v3.0\n"
            "Detects AI-like coding patterns using heuristics, AST analysis,\n"
            "cross-file similarity, and git metadata.\n\n"
            "⚠  Results are probabilistic patterns, NOT proof of authorship."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dirs", nargs="+", metavar="DIR", required=True,
                   help="Directories (repos) to scan.")
    p.add_argument("--output", choices=["table", "json", "csv"], default="table",
                   help="Output format (default: table).")
    p.add_argument("--include-tests", action="store_true",
                   help="Include test files in analysis (tracked separately).")
    p.add_argument("--exclude-tests", action="store_true",
                   help="Exclude test files entirely.")
    p.add_argument("--include-git", action="store_true",
                   help="Run git commit history analysis.")
    p.add_argument("--similarity", action="store_true",
                   help="Compute cross-file TF-IDF similarity (slower, O(n²)).")
    p.add_argument("--ast", action="store_true",
                   help="Enable Python AST structural analysis.")
    p.add_argument("--entropy", action="store_true",
                   help="Enable lexical entropy and TTR analysis.")
    p.add_argument("--workers", type=int, default=max(1, multiprocessing.cpu_count() - 1),
                   help="Parallel worker processes (default: cpu_count - 1).")
    p.add_argument("--no-color", action="store_true",
                   help="Disable ANSI color in table output.")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress progress output.")
    return p


# ── Per-file analysis (runs in worker process) ─────────────────────────────────

def _analyze_file(args: Tuple) -> Optional[FileAnalysis]:
    """
    Analyze a single file. Designed to run in a multiprocessing worker.
    Returns None if the file cannot be read or analyzed.
    """
    path, language, kind_name, enable_ast, enable_entropy = args

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    lines = text.count("\n") + 1
    signals: Dict[str, float] = {}

    # Heuristic signals (always enabled)
    signals.update(heuristics.compute_all(text, language))

    # AST structural analysis
    if enable_ast:
        signals.update(structural.analyze_structure(text, language))

    # Lexical entropy
    if enable_entropy:
        signals["token_entropy"]   = lexical.token_entropy(text)
        signals["type_token_ratio"]= lexical.type_token_ratio(text)
        signals["repetition_index"]= lexical.repetition_index(text)

    return score_file(
        path=path,
        language=language,
        kind=kind_name,
        lines=lines,
        signals=signals,
    )


# ── Repo-level orchestration ───────────────────────────────────────────────────

def scan_repo(
    root: Path,
    args: argparse.Namespace,
) -> Tuple[List[FileAnalysis], Optional[dict]]:
    """Scan a single repository and return (analyses, git_signals_dict)."""
    include_tests = args.include_tests and not args.exclude_tests

    # Discover files
    discovered = list(walk_repo(root, include_tests=include_tests))
    if not discovered:
        return [], None

    if not args.quiet:
        print(f"  → {root.name}: {len(discovered)} files found...", end=" ", flush=True)

    # Build worker args — use str(path) so they're picklable across processes
    worker_args = [
        (str(df.path), df.language, df.kind.name.lower(),
         args.ast, args.entropy)
        for df in discovered
    ]

    # Parallel file analysis (analyze_file is a top-level importable function)
    t0 = time.time()
    if args.workers > 1 and len(worker_args) > 20:
        with multiprocessing.Pool(processes=args.workers) as pool:
            results = pool.map(analyze_file, worker_args)
    else:
        results = [analyze_file(a) for a in worker_args]

    analyses = [r for r in results if r is not None]
    elapsed = time.time() - t0

    # Cross-file similarity injection
    if args.similarity and analyses:
        texts_by_lang: Dict[str, List[Tuple[int, str]]] = {}
        for i, (wargs, analysis) in enumerate(zip(worker_args, results)):
            if analysis is None:
                continue
            lang = wargs[1]
            try:
                text = Path(wargs[0]).read_text(encoding="utf-8", errors="ignore")
                texts_by_lang.setdefault(lang, []).append((i, text))
            except OSError:
                pass

        for lang, indexed_texts in texts_by_lang.items():
            if len(indexed_texts) < 3:
                continue
            indices, texts_list = zip(*indexed_texts)
            tf_vecs = [similarity.tokenize_file(t) for t in texts_list]
            sim_scores = similarity.compute_similarity_scores(tf_vecs)
            for idx, sim_val in zip(indices, sim_scores):
                analysis = results[idx]
                if analysis is None:
                    continue
                ai_sig = similarity.similarity_to_ai_signal(sim_val)
                updated_signals = dict(analysis.signals)
                updated_signals["similarity_cluster"] = ai_sig
                updated = score_file(
                    path=Path(analysis.path),
                    language=analysis.language,
                    kind=analysis.kind,
                    lines=analysis.lines,
                    signals=updated_signals,
                )
                results[idx] = updated

        analyses = [r for r in results if r is not None]

    # Git analysis
    git_sig = None
    if args.include_git:
        commits = get_commits(root)
        if commits:
            git_sig = git_signals.analyze_git(commits)

    if not args.quiet:
        ai_count = sum(1 for a in analyses if a.classification == "AI-like")
        print(f"{len(analyses)} analyzed  AI-like={ai_count}  [{elapsed:.1f}s]")

    return analyses, git_sig


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.output == "table":
        cli_reporter.print_disclaimer()

    all_repo_stats: List[RepoStats] = []
    all_analyses: Dict[str, List[FileAnalysis]] = {}

    for dir_str in args.dirs:
        root = Path(dir_str).resolve()
        if not root.exists():
            print(f"WARNING: {root} does not exist — skipped.", file=sys.stderr)
            continue

        analyses, git_sig = scan_repo(root, args)
        if not analyses:
            if not args.quiet:
                print(f"  → {root.name}: no scannable files found.")
            continue

        repo_name = root.name
        stats = calibrate_repo(repo_name, analyses, git_signals=git_sig)
        all_repo_stats.append(stats)
        all_analyses[repo_name] = analyses

    if not all_repo_stats:
        print("No files analyzed.", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output == "table":
        cli_reporter.print_multi_repo_table(all_repo_stats)
        for stats in all_repo_stats:
            cli_reporter.print_repo_summary(stats, use_color=not args.no_color)

    elif args.output == "json":
        report = json_report.build_report(
            all_stats=all_repo_stats,
            all_analyses=all_analyses,
            cli_args=vars(args),
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))

    elif args.output == "csv":
        import io
        buf = io.StringIO()
        buf.write("repo,file,language,kind,lines,ai_likelihood,confidence,classification\n")
        for repo_name, analyses in all_analyses.items():
            for a in analyses:
                buf.write(
                    f"{repo_name},{Path(a.path).name},{a.language},{a.kind},"
                    f"{a.lines},{a.ai_likelihood:.4f},{a.confidence:.4f},{a.classification}\n"
                )
        print(buf.getvalue(), end="")


if __name__ == "__main__":
    main()
