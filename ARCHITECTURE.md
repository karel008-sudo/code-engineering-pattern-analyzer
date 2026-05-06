# Architecture

This document is a high-level map for new contributors and reviewers. For full feature inventory, see [README.md](README.md). For implementation status, see [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

## Design principles

1. **Local-first** — no network, no telemetry, no source code leaves the machine
2. **Heuristic over speculative** — every signal has documented rationale, false-positive cases, and tests
3. **Pattern signals, not authorship proof** — output language never claims forensic certainty
4. **Anti-misuse by default** — developer fingerprinting disabled; per-developer rankings impossible by construction
5. **Stdlib-only core** — `pyyaml` optional; everything else is Python 3.8+ stdlib

## Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│  scan repository                                                      │
└──────────────────────┬───────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  scanners/filesystem.py — classify_file() → FileCategory             │
│    production_logic | dto_mapper | test | generated | vendor |       │
│    boilerplate_integ | config_infra | migration | example | notebook │
│  scanners/git.py — get_commits() with import/migration filtering     │
└──────────────────────┬───────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  analyzers/ — extract signals (per file)                             │
│    heuristics.py        12 language-specific code-style heuristics    │
│    structural.py        Python AST; Java regex approximation          │
│    lexical.py           token entropy, TTR, repetition index          │
│    similarity.py        TF-IDF cosine across repo (--similarity)      │
│    git_signals.py       burst (migration-filtered), diversity, entropy│
│    framework.py         Spring/JPA/Lombok/MapStruct/FastAPI/Pydantic  │
│    kotlin.py            data class (LOW signal), coroutines, Android  │
│    scaffold.py          completeness, magic numbers, name-body coh.   │
│    style_continuity.py  windowed style breaks, human irregularity     │
│    placeholder.py       LLM residue, generic literals, theater        │
│    test_quality.py      assertion quality, mock abuse, fixture realism│
│    pipeline.py          multiprocessing-safe worker; wires it all     │
└──────────────────────┬───────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  scoring/ — turn signals into scores                                 │
│    model.py        FileAnalysis v5.0; raw_score                       │
│    adjusted.py     category × framework × criticality adjustments     │
│    calibration.py  RepoStats; ModuleSummary; aggregation              │
└──────────────────────┬───────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  origin/ — three-way Origin Pattern Estimate                         │
│    engine.py       compute_file_origin() with 8 modifier categories;  │
│                    skipped for GENERATED and VENDOR                   │
│                    (tool-generated ≠ LLM-generated)                   │
│    confidence.py   ConfidenceInterval; portfolio_interval()           │
└──────────────────────┬───────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  reporting/ — render results                                         │
│    cli.py          terminal output, AI-Adoption Pattern Index         │
│    json_report.py  schema v5.0, portfolio_origin_estimate             │
│    markdown.py     Markdown leadership report                         │
│    sarif.py        SARIF 2.1.0 for code-scanning integration          │
└──────────────────────────────────────────────────────────────────────┘
```

## Key concepts

### FileCategory (semantic classification)

Every file gets a category **before** scoring. Generated and vendor files are excluded from KPI and from origin estimates entirely — tool-generated code is not the same concept as LLM-generated code, and conflating them is the most common analyzer mistake.

### Multi-score model

| Score | Meaning |
|---|---|
| `ai_likelihood` | Raw heuristic aggregate, sigmoid-normalized |
| `adjusted_score` | Context-adjusted (category × framework × criticality) — the **primary** interpretation metric |
| `risk_score` | Engineering review priority. Not the same as AI-likeness. |
| `confidence` | Signal agreement fraction |
| `kpi_score` | AI-Adoption Pattern Index — production logic only, KPI-eligible only |
| `origin_estimate` | Three-way distribution: AI-like / AI-assisted / human-pattern. Always sums to 100%. |

### Origin Pattern Estimate

This is the headline KPI of v5.0. It is **not** a percentage of files written by AI. It is a heuristic three-way distribution over code pattern signals, with explicit confidence intervals and mandatory caveats embedded in every output.

The model lives in `origin/engine.py` and applies eight categories of modifiers to a baseline distribution: scaffold completeness, magic-number discipline, name-body coherence, style continuity, human irregularity, framework context, file category, and git temporal signals.

### Confidence intervals

Each estimate carries a `confidence_level` (high / medium / low) and a `ConfidenceInterval` per dimension. Width is heuristic (±6 / ±12 / ±22 percentage points) — not based on statistical sampling. Files with `confidence: low` are treated as inconclusive in the CLI and Markdown outputs.

## Data flow boundaries

```
┌─ External world ─┐         ┌─ Analyzer process ─┐         ┌─ Output ─┐
│ git CLI         │ ──────▶ │ multiprocessing   │ ──────▶ │ stdout   │
│ source files    │ (read)  │ workers           │ (write) │ files    │
│ ai-analyzer.yml │         │                   │         │ (no PII) │
└─────────────────┘         └───────────────────┘         └──────────┘
```

No outbound network. No subprocess execution of analyzed code. The only external process is `git` (when `--include-git` is set), invoked read-only.

## Extension points

Areas where the architecture supports future work but does not ship implementations:

- **JavaParserAdapter** — for full Java AST via tree-sitter or javalang
- **HistoricalBaselineAnalyzer** — per-file git timestamp baselines
- **Recent-code window** — per-file blame-based recency
- **Diff mode** — CLI flags exist; engine implementation is a stub
- **Velocity/quality correlation** — requires PR/review/defect metadata
- **Temporal visualization** — requires multi-scan history storage

See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for full status of all 83 v5.0 + 303 v4.0 requirements.

## Testing strategy

170 tests across 11 modules. Organized by concern:

- **Heuristic correctness** — does each signal trigger on expected inputs and not on counter-examples?
- **Sum-to-100 invariants** — five dedicated tests verifying origin estimates always sum to 100% across score ranges
- **Wording safety** — `test_wording_safety.py` (17 tests) verifies the analyzer never claims forensic certainty in any output format
- **Vendor/generated exclusion** — `test_vendor_paths.py` (20 tests) covers all known vendor and generated path patterns
- **Regression** — all v4.0 tests still pass unchanged
