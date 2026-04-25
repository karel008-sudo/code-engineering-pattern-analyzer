"""
__main__.py — CLI entry point for Code Engineering Pattern Analyzer v4.0.

Usage examples:
  python -m ai_pattern_analyzer --dirs ./my-repo
  python -m ai_pattern_analyzer --dirs ./repo --profile full --format json
  python -m ai_pattern_analyzer --dirs ./repo --profile ci --format sarif > findings.sarif
  python -m ai_pattern_analyzer --dirs ./repo --profile leadership --format markdown
  python -m ai_pattern_analyzer --dirs ./repo --config ./ai-analyzer.yaml
  python -m ai_pattern_analyzer --generate-config > ai-analyzer.yaml

⚠ Results are probabilistic pattern signals — NOT proof of AI authorship.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .scanners.filesystem import FileKind, walk_repo
from .scanners.git import get_commits
from .analyzers import similarity, git_signals
from .analyzers.pipeline import analyze_file
from .scoring.model import FileAnalysis, score_file
from .scoring.calibration import RepoStats, calibrate_repo
from .reporting import cli as cli_reporter, json_report
from .reporting.markdown import build_markdown_report
from .reporting.sarif import build_sarif_report
from .config import EXTENSION_TO_LANG, ANALYZER_VERSION
from .config_file import load_config, generate_example_config
from .domain import ScanConfig, FileCategory


# ── Argument parsing ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m ai_pattern_analyzer",
        description=(
            f"Code Engineering Pattern Analyzer v{ANALYZER_VERSION}\n"
            "Detects AI-like, automation-like, and generated-code patterns using\n"
            "heuristics, AST analysis, cross-file similarity, and git metadata.\n\n"
            "⚠  Results are probabilistic pattern signals, NOT proof of AI authorship.\n"
            "   Do NOT use for individual developer evaluation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Required ───────────────────────────────────────────────────────────────
    p.add_argument("--dirs", nargs="+", metavar="DIR",
                   help="Directories (repositories) to scan.")

    # ── Scan profile ──────────────────────────────────────────────────────────
    p.add_argument(
        "--profile",
        choices=["quick", "ci", "full", "forensic", "leadership", "calibration", "default"],
        default="default",
        help=(
            "Scan profile (default: default). Profiles preset feature flags:\n"
            "  quick:       lexical + heuristic only, fast\n"
            "  ci:          ast + entropy + git, no similarity\n"
            "  full:        all features including similarity\n"
            "  forensic:    full + snippets in output\n"
            "  leadership:  full + markdown output\n"
            "  calibration: full + debug + profiling"
        ),
    )

    # ── Output format ─────────────────────────────────────────────────────────
    p.add_argument(
        "--format", dest="output",
        choices=["table", "json", "markdown", "csv", "sarif"],
        default=None,
        help="Output format. Default depends on profile (table for default, markdown for leadership).",
    )

    # ── Feature flags ─────────────────────────────────────────────────────────
    p.add_argument("--ast", action="store_true",
                   help="Enable Python AST structural analysis.")
    p.add_argument("--entropy", action="store_true",
                   help="Enable lexical entropy and TTR analysis.")
    p.add_argument("--similarity", action="store_true",
                   help="Compute cross-file TF-IDF similarity (slower, O(n²)).")
    p.add_argument("--include-git", action="store_true",
                   help="Run git commit history analysis.")

    # ── File filtering ────────────────────────────────────────────────────────
    p.add_argument("--include-tests", action="store_true",
                   help="Include test files in analysis (tracked separately).")
    p.add_argument("--exclude-tests", action="store_true",
                   help="Exclude test files entirely.")

    # ── Config ────────────────────────────────────────────────────────────────
    p.add_argument("--config", metavar="FILE",
                   help="Path to ai-analyzer.yaml config file.")
    p.add_argument("--generate-config", action="store_true",
                   help="Print an example ai-analyzer.yaml to stdout and exit.")

    # ── CI/CD ─────────────────────────────────────────────────────────────────
    p.add_argument("--fail-on-policy", action="store_true",
                   help="Exit with code 1 if policy conditions are met (requires config).")
    p.add_argument("--baseline", metavar="FILE",
                   help="Baseline JSON report for delta comparison.")

    # ── Performance ───────────────────────────────────────────────────────────
    p.add_argument("--workers", type=int,
                   default=max(1, multiprocessing.cpu_count() - 1),
                   help="Parallel worker processes (default: cpu_count - 1).")
    p.add_argument("--profile-performance", action="store_true",
                   help="Output per-file analysis timing.")

    # ── Output options ────────────────────────────────────────────────────────
    p.add_argument("--include-snippets", action="store_true",
                   help="Include code snippets in findings (forensic mode).")
    p.add_argument("--exclude-low-confidence-from-kpi", action="store_true",
                   help="Exclude files with confidence < 0.40 from KPI calculation.")
    p.add_argument("--no-color", action="store_true",
                   help="Disable ANSI color in table output.")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress progress output.")
    p.add_argument("--debug-rules", action="store_true",
                   help="Show signal values per file.")

    return p


# ── Worker args builder ────────────────────────────────────────────────────────

def _build_worker_args(
    discovered_files: list,
    scan_config: ScanConfig,
    critical_paths: List[str],
    has_git: bool,
) -> List[Tuple]:
    """Build args tuples for multiprocessing workers."""
    import re
    critical_patterns = [re.compile(p, re.I) for p in critical_paths]

    def _is_critical(path_str: str) -> bool:
        return any(pat.search(path_str) for pat in critical_patterns)

    return [
        (
            str(df.path),
            df.language,
            df.kind.name.lower(),
            df.category.value,
            scan_config.enable_ast,
            scan_config.enable_entropy,
            scan_config.enable_framework_detection,
            scan_config.enable_placeholder_detection,
            scan_config.enable_test_quality,
            _is_critical(str(df.path)),
            has_git,
            df.module_path,
        )
        for df in discovered_files
    ]


# ── Repo-level orchestration ───────────────────────────────────────────────────

def scan_repo(
    root: Path,
    scan_config: ScanConfig,
    args: argparse.Namespace,
) -> Tuple[List[FileAnalysis], Optional[dict]]:
    """Scan a single repository and return (analyses, git_signals_dict)."""
    include_tests = (scan_config.include_tests and not scan_config.exclude_tests)

    discovered = list(walk_repo(
        root,
        include_tests=include_tests,
        ignored_paths=scan_config.ignored_paths,
    ))
    if not discovered:
        return [], None

    if not scan_config.quiet:
        print(f"  → {root.name}: {len(discovered)} files found...", end=" ", flush=True)

    # Git analysis first (needed as context for worker args)
    git_sig = None
    commits = []
    has_git = False
    if scan_config.enable_git:
        commits = get_commits(root)
        if commits:
            git_sig = git_signals.analyze_git(commits)
            has_git = True

    # Build worker args
    worker_args = _build_worker_args(
        discovered_files=discovered,
        scan_config=scan_config,
        critical_paths=scan_config.critical_paths,
        has_git=has_git,
    )

    # Parallel file analysis
    t0 = time.time()
    if scan_config.workers > 1 and len(worker_args) > 20:
        with multiprocessing.Pool(processes=scan_config.workers) as pool:
            results = pool.map(analyze_file, worker_args)
    else:
        results = [analyze_file(a) for a in worker_args]

    analyses = [r for r in results if r is not None]
    elapsed = time.time() - t0

    # Cross-file similarity injection
    if scan_config.enable_similarity and analyses:
        _apply_similarity(results, worker_args, analyses, scan_config)
        analyses = [r for r in results if r is not None]

    if not scan_config.quiet:
        ai_count = sum(1 for a in analyses if a.classification == "AI-like")
        print(f"{len(analyses)} analyzed  AI-like={ai_count}  [{elapsed:.1f}s]")

    return analyses, git_sig


def _apply_similarity(
    results: list,
    worker_args: list,
    analyses: list,
    scan_config: ScanConfig,
) -> None:
    """Inject cross-file similarity signals into results (mutates results in-place)."""
    from .analyzers import similarity as sim_mod

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
        tf_vecs = [sim_mod.tokenize_file(t) for t in texts_list]
        sim_scores = sim_mod.compute_similarity_scores(tf_vecs)

        for idx, sim_val in zip(indices, sim_scores):
            analysis = results[idx]
            if analysis is None:
                continue
            ai_sig = sim_mod.similarity_to_ai_signal(sim_val)
            updated_signals = dict(analysis.signals)
            updated_signals["similarity_cluster"] = ai_sig
            wargs = worker_args[idx]
            updated = score_file(
                path=Path(wargs[0]),
                language=analysis.language,
                kind=analysis.kind,
                lines=analysis.lines,
                signals=updated_signals,
                category=analysis.category,
                framework_ctx=analysis.framework_context,
                is_critical_path=wargs[9],
                has_git=wargs[10],
                module_path=analysis.module_path,
            )
            results[idx] = updated


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Generate config example and exit
    if args.generate_config:
        print(generate_example_config())
        sys.exit(0)

    if not args.dirs:
        parser.error("--dirs is required unless --generate-config is used")

    # Load config file
    config_path = Path(args.config) if args.config else None
    scan_dir    = Path(args.dirs[0]).resolve() if args.dirs else None
    scan_config = load_config(config_path, scan_dir=scan_dir)

    # Apply profile first (sets defaults)
    profile_config = ScanConfig.from_profile(args.profile)
    # Profile defaults — only override if not explicitly set in file config
    if args.profile != "default":
        scan_config.enable_ast         = profile_config.enable_ast
        scan_config.enable_entropy     = profile_config.enable_entropy
        scan_config.enable_similarity  = profile_config.enable_similarity
        scan_config.enable_git         = profile_config.enable_git

    # Apply explicit CLI flags (highest priority)
    if args.ast:           scan_config.enable_ast        = True
    if args.entropy:       scan_config.enable_entropy    = True
    if args.similarity:    scan_config.enable_similarity = True
    if args.include_git:   scan_config.enable_git        = True
    if args.include_tests: scan_config.include_tests     = True
    if args.exclude_tests: scan_config.exclude_tests     = True
    if args.fail_on_policy: scan_config.fail_on_policy   = True
    if args.include_snippets: scan_config.include_snippets = True

    scan_config.workers       = args.workers
    scan_config.quiet         = args.quiet
    scan_config.use_color     = not args.no_color
    scan_config.profile       = args.profile
    scan_config.debug_rules   = args.debug_rules
    scan_config.profile_performance = args.profile_performance

    # Determine output format
    output_fmt = args.output
    if output_fmt is None:
        output_fmt = scan_config.output_format
        if args.profile == "leadership" and output_fmt == "table":
            output_fmt = "markdown"

    # Print disclaimer for table output
    if output_fmt == "table":
        cli_reporter.print_disclaimer()

    all_repo_stats: List[RepoStats] = []
    all_analyses: Dict[str, List[FileAnalysis]] = {}

    for dir_str in args.dirs:
        root = Path(dir_str).resolve()
        if not root.exists():
            print(f"WARNING: {root} does not exist — skipped.", file=sys.stderr)
            continue

        analyses, git_sig = scan_repo(root, scan_config, args)
        if not analyses:
            if not scan_config.quiet:
                print(f"  → {root.name}: no scannable files found.")
            continue

        repo_name = root.name
        stats = calibrate_repo(
            repo_name=repo_name,
            analyses=analyses,
            git_signals=git_sig,
            has_git=scan_config.enable_git,
            has_ast=scan_config.enable_ast,
        )
        all_repo_stats.append(stats)
        all_analyses[repo_name] = analyses

    if not all_repo_stats:
        print("No files analyzed.", file=sys.stderr)
        sys.exit(1)

    # ── Output ────────────────────────────────────────────────────────────────
    if output_fmt == "table":
        cli_reporter.print_multi_repo_table(all_repo_stats)
        for stats in all_repo_stats:
            cli_reporter.print_repo_summary(stats, use_color=not args.no_color)

    elif output_fmt == "json":
        report = json_report.build_report(
            all_stats=all_repo_stats,
            all_analyses=all_analyses,
            cli_args=vars(args),
            include_snippets=scan_config.include_snippets,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))

    elif output_fmt == "markdown":
        md = build_markdown_report(
            all_stats=all_repo_stats,
            all_analyses=all_analyses,
            scan_config=scan_config,
        )
        print(md)

    elif output_fmt == "sarif":
        sarif = build_sarif_report(all_analyses=all_analyses)
        print(json.dumps(sarif, indent=2, ensure_ascii=False))

    elif output_fmt == "csv":
        import io
        buf = io.StringIO()
        buf.write(
            "repo,file,language,category,kind,lines,"
            "ai_likelihood,adjusted_score,risk_score,confidence,classification,recommendation\n"
        )
        for repo_name, analyses in all_analyses.items():
            for a in analyses:
                buf.write(
                    f"{repo_name},{Path(a.path).name},{a.language},"
                    f"{a.category.value},{a.kind},{a.lines},"
                    f"{a.ai_likelihood:.4f},{a.adjusted_score:.4f},"
                    f"{a.risk_score:.4f},{a.confidence:.4f},"
                    f"{a.classification},{a.review_recommendation}\n"
                )
        print(buf.getvalue(), end="")

    # ── Policy check ──────────────────────────────────────────────────────────
    if scan_config.fail_on_policy:
        policy_violation = False
        for stats in all_repo_stats:
            if stats.high_risk_count > 0 and stats.kpi_score > 0.55:
                policy_violation = True
                print(
                    f"POLICY VIOLATION: {stats.repo_name} has "
                    f"{stats.high_risk_count} high-risk files and KPI score "
                    f"{stats.kpi_score:.1%}.",
                    file=sys.stderr,
                )
        if policy_violation:
            sys.exit(1)


if __name__ == "__main__":
    main()
