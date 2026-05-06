# Code Engineering Pattern Analyzer v5.0

[![CI](https://github.com/karel008-sudo/code-engineering-pattern-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/karel008-sudo/code-engineering-pattern-analyzer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-170%20passing-brightgreen)](tests/)
[![Local-first](https://img.shields.io/badge/local--first-no%20external%20calls-informational)](#privacy-and-security)
[![Languages](https://img.shields.io/badge/languages-Python%20%7C%20Java%20%7C%20Kotlin-blue)](#language-support-matrix)
[![Schema](https://img.shields.io/badge/schema-v5.0-blueviolet)](IMPLEMENTATION_STATUS.md)

A **local-first, heuristic analyzer** that estimates AI-like, AI-assisted, automation-like, and generated-code characteristics in Python, Java, and Kotlin repositories. Operates entirely offline — no ML models, no external APIs, no LLM calls, no source code leaves the machine.

> **Critical framing:** This tool does **not** detect AI-generated code with certainty.
> It measures heuristic signals statistically associated with generated, scaffolded, AI-assisted, or mechanically produced code.
> Results are **directional pattern estimates**, not forensic proof of AI origin.
> Must not be used to evaluate individual developers.

---

## Contents

- [What this tool does (and does not)](#what-this-tool-does)
- [Quick start](#quick-start)
- [AI Origin Pattern Estimate](#ai-origin-pattern-estimate)
- [AI-Adoption Pattern Index](#ai-adoption-pattern-index)
- [Scan profiles](#scan-profiles)
- [Multi-score model](#multi-score-model)
- [File classification](#file-classification)
- [Methodology](#methodology)
- [Scoring interpretation](#scoring-interpretation)
- [False positives and negatives](#false-positives-and-negatives)
- [Privacy and security](#privacy-and-security)
- [CLI reference](#cli-reference)
- [Config file](#config-file)
- [Output formats](#output-formats)
- [Language support matrix](#language-support-matrix)
- [Architecture](#architecture)
- [Comparison with industry tools](#comparison-with-industry-tools)
- [Ethics and anti-misuse](#ethics-and-anti-misuse)
- [Limitations](#limitations)
- [Implementation status](#implementation-status)
- [Requirements](#requirements)

---

## What this tool does

The analyzer scans source code repositories and produces per-file and per-repository estimates of:

- **AI Origin Pattern Estimate** — three-way distribution: fully AI-like / AI-assisted / human-like code patterns
- **AI-Adoption Pattern Index** — repository-level directional KPI (not "% of files written by AI")
- **Engineering risk score** — which files most need manual review
- **Test quality signals** — shallow assertions, mock abuse, generic fixtures
- **Generated-code ratio** — how much is protobuf, OpenAPI, vendored, or tool-generated

Suitable for:
- Repository-level trend monitoring
- Team-level AI adoption pattern proxy
- Generated-code governance
- Manual review prioritization
- AI readiness analysis

**Not suitable for:** proving individual AI usage, contractual claims, legal evidence, disciplinary action.

---

## Quick start

```bash
# Default scan
python3 -m ai_pattern_analyzer --dirs ./my-repo

# Full analysis with AST, entropy, git, framework detection
python3 -m ai_pattern_analyzer --dirs ./repo --profile full

# Leadership Markdown summary
python3 -m ai_pattern_analyzer --dirs ./repo --profile leadership --format markdown

# CI pipeline scan
python3 -m ai_pattern_analyzer --dirs ./repo --profile ci --format json > report.json

# Explain a specific file in detail
python3 -m ai_pattern_analyzer --dirs ./repo --explain ./repo/src/Service.java

# Explain repository origin pattern estimate
python3 -m ai_pattern_analyzer --dirs ./repo --explain-repo

# SARIF output for code scanning systems
python3 -m ai_pattern_analyzer --dirs ./repo --profile full --format sarif > findings.sarif

# Generate config template
python3 -m ai_pattern_analyzer --generate-config > ai-analyzer.yaml
```

---

## AI Origin Pattern Estimate

v5.0 introduces a **three-way heuristic pattern estimate** per file and repository:

```
AI Origin Pattern Estimate
──────────────────────────
⚠ Pattern estimates only — NOT proof of actual authorship

Fully AI-like pattern signals:   4.2%   confidence: medium   interval: 0.0–10.2%
AI-assisted pattern signals:    52.3%   confidence: medium   interval: 44.3–60.3%
Human-pattern signals:          43.5%   confidence: medium   interval: 35.5–51.5%

Sum: 100.0%  |  Generated/vendor files excluded
```

### What the three categories mean

| Category | Patterns detected | What it does NOT mean |
|---|---|---|
| **Fully AI-like** | High structural homogeneity, scaffold completeness, prompt residue, low human irregularity, large homogeneous commits | Code was proven to be generated by an LLM |
| **AI-assisted** | Style discontinuities, mixed signal sections, moderate AI-like score, documentation drift, Copilot-like incremental patterns | Code was proven to be Copilot-assisted |
| **Human-pattern** | Organic irregularity, legacy idioms, gradual git history, magic numbers, domain vocabulary, manual exception patterns | Code was proven to be written without AI tools |

### Critical limitations

- These are **heuristic pattern signals**, not forensic proof of authorship
- All three probabilities have known false positive and false negative rates
- **Tool-generated code** (protobuf, OpenAPI, jOOQ) is explicitly **excluded** — it is not the same concept as "LLM-generated" and has no origin estimate
- Clean senior code, strict formatters, and framework boilerplate appear AI-like regardless of actual origin
- Kotlin data classes, Java DTOs, Spring controllers are inherently regular — they lower AI-origin interpretation
- Files with `confidence: low` should be treated as inconclusive

---

## AI-Adoption Pattern Index

The **AI-Adoption Pattern Index** is the repository-level KPI. It ranges from 0–100%.

```
AI-Adoption Pattern Index:  35.5% [MODERATE]
⚠ This is NOT a percentage of AI-generated files.
  It is a directional KPI based on code pattern signals.
```

| Band | Range | Interpretation |
|---|---|---|
| LOW | 0–25% | Low AI-like signal density. Consistent with established codebases. |
| MODERATE | 26–50% | Moderate signals. May reflect formatters, framework patterns, or AI adoption. |
| ELEVATED | 51–75% | Elevated signals. Warrants contextual review. |
| HIGH | 76–100% | High density. Check for generated clients, DTOs, or scaffold generation. |

**This index is NOT "the percentage of code written by AI."** It is a code-style pattern metric. Use it directionally and comparatively, not as an absolute measure.

---

## Scan profiles

| Profile | AST | Entropy | Similarity | Git | v5.0 Analyzers | Output |
|---|---|---|---|---|---|---|
| `quick` | ✗ | ✗ | ✗ | ✗ | ✓ | table |
| `default` | ✗ | ✗ | ✗ | ✗ | ✓ | table |
| `ci` | ✓ | ✓ | ✗ | ✓ | ✓ | table/json |
| `full` | ✓ | ✓ | ✓ | ✓ | ✓ | json |
| `forensic` | ✓ | ✓ | ✓ | ✓ | ✓ | json+snippets |
| `leadership` | ✓ | ✓ | ✗ | ✓ | ✓ | markdown |
| `calibration` | ✓ | ✓ | ✓ | ✓ | ✓ | json+debug |

---

## Multi-score model

v5.0 introduces multiple score dimensions:

| Score | Range | Description |
|---|---|---|
| `ai_likelihood` | 0–1 | Raw heuristic aggregate, sigmoid-normalized |
| `adjusted_score` | 0–1 | Context-adjusted (category, framework, criticality) |
| `risk_score` | 0–1 | Engineering review priority (≠ AI-likeness) |
| `confidence` | 0–1 | Signal agreement fraction |
| `kpi_score` | 0–1 | AI-Adoption Pattern Index (production logic, KPI-eligible only) |
| `origin_estimate` | three-way | AI-like / AI-assisted / human-pattern percentages |

### raw_score vs adjusted_score

**Raw score** reflects heuristic signals only, without context.

**Adjusted score** accounts for:
- **File category**: DTOs, mappers, generated code are expected to be regular; adjusted downward
- **Framework context**: Spring, JPA, Pydantic, MapStruct enforce patterns that appear AI-like; adjusted downward
- **Critical paths**: files in `critical_paths` get higher risk scores

### risk_score

Combines adjusted AI-like signal × confidence × category weight × criticality flag.
A high risk_score means "this file warrants review" — not "this file was AI-generated."

---

## File classification

Every file is classified into a semantic category before scoring. Category affects interpretation and adjusted score.

| Category | KPI weight | Examples |
|---|---|---|
| `production_logic` | 1.00 | Service classes, domain logic |
| `dto_mapper` | 0.60 | DTOs, request/response classes, MapStruct mappers |
| `test` | 0.80 | Test classes, pytest files |
| `generated` | **excluded** | Protobuf stubs, OpenAPI clients, jOOQ generated |
| `boilerplate_integ` | 0.55 | Spring Boot config, application startup |
| `config_infra` | 0.70 | application.yml, pom.xml, Dockerfile |
| `migration` | 0.65 | Flyway, Alembic, Liquibase |
| `example` | **excluded** | Demos, tutorials, playground |
| `vendor` | **excluded** | Vendored third-party code |
| `notebook` | 0.75 | Jupyter notebooks |

Generated, vendor, and example files are excluded from KPI and from the AI Origin Pattern Estimate. The report shows how many files were excluded and why. **Tool-generated code (protobuf, OpenAPI, jOOQ) is explicitly not classified as "LLM-generated"** — it has no origin estimate.

Vendor detection covers: `vendor/`, `vendored/`, `deps/`, `Pods/`, `Carthage/`, `site-packages/`, `node_modules/`, and common package structure prefixes.

Generated detection covers: `proto/`, `grpc/`, `avro/`, `swagger/`, `openapi/`, `kapt-generated/`, `apt-generated/`, `jooq-generated/`, `graphql-generated/`, and generated-code headers.

---

## Methodology

### Analysis layers

| Layer | Description | Flag |
|---|---|---|
| Heuristic signals | 34 language-specific code-style signals | Always |
| Framework detection | Spring, JPA, Lombok, MapStruct, FastAPI, Pydantic, Django | Always |
| File classification | Semantic FileCategory for context-aware scoring | Always |
| Placeholder/LLM residue | Instructional comments, generic literals, resilience theater | Always |
| Scaffold completeness | Method length uniformity, CRUD pattern detection | Always (v5.0) |
| Magic number discipline | Unnamed literal density (safe values excluded) | Always (v5.0) |
| Name-body coherence | Alignment between function names and implementation | Always (v5.0) |
| Style continuity | Windowed style break detection (40-line windows) | Always (v5.0) |
| Human irregularity | Bare except, print-debugging, magic numbers, naming mix | Always (v5.0) |
| Kotlin-native heuristics | Data class, coroutines, nullability, Android patterns | Always (Kotlin) |
| Test quality | Assertion quality, mock abuse, fixture realism | Always (test files) |
| Structural motifs | Method-level structural pattern uniformity | Always |
| AST structural | Python AST: depth, node diversity, function length | `--ast` |
| Lexical entropy | Shannon entropy, type-token ratio, shingle repetition | `--entropy` |
| Cross-file similarity | TF-IDF cosine similarity across repository | `--similarity` |
| Git metadata | Commit burst detection, author diversity, message entropy | `--include-git` |

### Git burst detection (v5.0 improved)

Large commits are **not automatically interpreted as AI bursts**. v5.0 filters out:
- Initial repository imports
- CVS/SVN migrations
- Refactoring and formatting runs
- Generated code updates (OpenAPI regeneration)
- Vendor syncs and mirrors

Commit message keywords detected: `initial import`, `cvs`, `svn`, `migrate`, `refactor`, `reformat`, `format`, `cleanup`, `generated`, `regenerate`, `vendored`, `sync`, `mirror`, `cherry-pick`, `squash`.

### Kotlin-native heuristics (v5.0)

Kotlin idioms are **intentionally given low AI signals**:
- `data class`, `sealed class`, `value class` → LOW signal (idiomatic, not AI-specific)
- `suspend fun`, `Flow`, coroutine scopes → MODERATE/contextual signal
- `?:`, `?.`, `!!`, null-safety operators → LOW signal (idiomatic)
- Android framework patterns (Activity, ViewModel, Composable) → **REDUCES** AI score (framework boilerplate)

### Scaffold completeness

Detects structurally symmetrical files:
- Uniform method length distribution (low coefficient of variation)
- Complete CRUD pattern (findById, save, delete, findAll all present)
- Uniform error handling and validation across methods

High completeness increases fully-AI-like pattern probability — but framework generators (Spring, MapStruct) provide alternative explanations.

### Style continuity

Files are split into 40-line windows. A 5-feature style vector (line length, comment density, blank ratio, token length, indent consistency) is computed per window. Style discontinuities between windows suggest **AI-assisted** editing (localized AI block in human-written file) rather than full AI generation.

---

## Scoring interpretation

| Score Band | Range | Interpretation |
|---|---|---|
| **Low** | 0–25% | Patterns consistent with typical hand-written code |
| **Moderate** | 26–50% | May reflect tooling, framework conventions, or AI-assisted development |
| **Elevated** | 51–75% | Warrants contextual review |
| **High** | 76–100% | Strong AI-like or generated-like characteristics. Not proof of AI origin. |

The **adjusted score** (not raw likelihood) is the primary interpretation metric. Low confidence (`< 0.45`) → treat classification as inconclusive.

---

## False positives and negatives

### False positives (elevated score, not AI-generated)

- **Senior developer code**: Clean, consistent, well-structured code
- **Strict formatters**: Black, google-java-format, isort, Prettier
- **Kotlin data classes**: Language-native, not AI-specific (intentionally given low weight)
- **Spring Boot / JPA entities**: Framework conventions that enforce regularity
- **MapStruct mappers**: By design symmetric and annotation-driven
- **Pydantic models**: Require uniform field definitions by convention
- **DTOs / request-response classes**: Inherently regular; adjusted score accounts for this
- **Generated clients**: OpenAPI, Protobuf, jOOQ — explicitly excluded from KPI and origin estimate
- **Heavy refactoring**: Large uniform cleanup passes
- **Old code imported from CVS/SVN**: Burst detection now filters these

### False negatives (low score, may be AI-assisted)

- **Human-edited AI output**: Developer rewrote or refactored AI-generated code
- **Copilot incremental suggestions**: Small completions accepted across many commits
- **Intentionally irregular AI code**: Prompted to match existing style
- **Terse utility functions**: Few AI-like signals in short code
- **Mixed-origin files**: Score reflects aggregate; individual sections may differ
- **No git history**: Temporal signals unavailable; confidence reduced

---

## Privacy and security

- **No source code leaves the machine**: All analysis runs locally. No API calls.
- **Air-gapped compatible**: No network dependencies whatsoever.
- **No code execution**: The analyzer reads source text only. It never imports or executes analyzed code.
- **No secret extraction**: The analyzer does not extract or log secrets, credentials, or PII.
- **Developer fingerprint**: `developer_fingerprint_enabled = false` by default. If enabled, requires explicit config, shows ethics warning, and never outputs individual rankings.

---

## CLI reference

```
python3 -m ai_pattern_analyzer [OPTIONS]

Required:
  --dirs DIR [DIR ...]          Repositories to scan

Scan profile:
  --profile PROFILE             quick | ci | full | forensic | leadership | calibration

Output:
  --format FORMAT               table | json | markdown | csv | sarif

Feature flags (override profile):
  --ast                         Enable Python AST structural analysis
  --entropy                     Enable lexical entropy and TTR analysis
  --similarity                  Compute cross-file TF-IDF similarity (O(n²))
  --include-git                 Analyze git commit history

File filtering:
  --include-tests               Include test files in analysis
  --exclude-tests               Exclude test files entirely

Explain mode (v5.0):
  --explain FILE                Full explanation for a specific file
  --explain-repo                Repository AI Origin Pattern Estimate report

Config:
  --config FILE                 Path to ai-analyzer.yaml
  --generate-config             Print example config to stdout

KPI control (v5.0):
  --include-generated-in-kpi    Include generated files in KPI (default: excluded)
  --include-vendor-in-kpi       Include vendor files in KPI (default: excluded)

Diff/comparison (extension points):
  --diff-mode                   Analyze only changed files
  --base REF                    Base ref for diff mode (default: main)
  --head REF                    Head ref for diff mode (default: HEAD)
  --changed-only                Scan only files changed since --base
  --compare FILE                Compare against a previous scan JSON

CI/CD:
  --fail-on-policy              Exit 1 if policy conditions are met
  --baseline FILE               Baseline JSON for delta comparison

Performance:
  --workers N                   Parallel worker processes (default: cpu_count - 1)

Output options:
  --include-snippets            Include code snippets in findings (forensic)
  --no-color                    Disable ANSI color
  --quiet                       Suppress progress output
  --debug-rules                 Show signal values per file
```

---

## Config file

```bash
python3 -m ai_pattern_analyzer --generate-config > ai-analyzer.yaml
```

Key options:

```yaml
# ai-analyzer.yaml — Code Engineering Pattern Analyzer v5.0

scoring_model_version: "5.0"
ruleset_version: "5.0"

ignored_paths:
  - "target/"
  - "build/"
  - "node_modules/"
  - ".venv/"

generated_paths:
  - "*/generated/**"
  - "*/openapi-client/**"

critical_paths:
  - "*/billing/**"
  - "*/payment/**"

domain_terms:
  - "subscription"
  - "tariff"
  - "customer"

# KPI control — generated/vendor excluded by default
include_vendor_in_kpi: false
include_generated_in_kpi: false

# Historical baseline cutoff for baseline comparison
historical_baseline_cutoff: "2022-01-01"

# Recent code analysis window
recent_code_window_months: 12

# Developer fingerprint — DISABLED BY DEFAULT (ethics guardrail)
# developer_fingerprint_enabled: false

privacy_mode: local   # local | safe | hash

thresholds:
  ai_high: 0.68
  ai_low: 0.62
  min_confidence: 0.45

fail_on_policy: false
```

---

## Output formats

### Table (default)
Terminal output with AI-Adoption Pattern Index, AI Origin Pattern Estimate, module heatmap, category breakdown, risk files, and git signals.

### JSON (`--format json`)
Full structured report — schema version 5.0. Includes:
- `portfolio_origin_estimate` with three-way distribution and confidence intervals
- Per-repo `origin_estimate`
- Per-file `origin_estimate` (production/test files only; `null` for generated/vendor)
- `pct_note` disclaimer in every origin estimate
- `caveats` list in every origin estimate
- `false_positive_candidates`, `high_confidence_candidates`

```json
{
  "schema_version": "5.0",
  "portfolio_origin_estimate": {
    "fully_ai_generated_pct": 3.2,
    "ai_assisted_pct": 48.1,
    "human_authored_pct": 48.7,
    "pct_note": "These percentages reflect heuristic code-pattern signals. They do not constitute proof of actual authorship or AI tool usage.",
    "confidence": "medium",
    "confidence_interval": {
      "fully_ai_generated": {"low": 0.0, "high": 9.2},
      "ai_assisted": {"low": 40.1, "high": 56.1},
      "human_authored": {"low": 40.7, "high": 56.7}
    },
    "caveats": [
      "These are heuristic pattern estimates, not forensic proof of AI authorship.",
      "Generated files (proto, OpenAPI, jOOQ) are excluded from this estimate.",
      "Must not be used for individual developer evaluation."
    ]
  },
  "repos": [{
    "repo": "my-repo",
    "origin_estimate": { "..." },
    "files": [{
      "path": "src/Service.java",
      "category": "production_logic",
      "ai_likelihood": 0.42,
      "adjusted_score": 0.31,
      "risk_score": 0.18,
      "origin_estimate": {
        "fully_ai_generated_pct": 5.1,
        "ai_assisted_pct": 44.2,
        "human_authored_pct": 50.7,
        "confidence": "medium"
      }
    }]
  }]
}
```

### Markdown (`--format markdown`)
Human-readable report with executive summary, AI Origin Pattern Estimate, module heatmap, review candidates. Footnotes clarify that "high-signal files" ≠ "AI-written files".

### CSV (`--format csv`)
One row per file with: repo, file, language, category, kind, lines, ai_likelihood, adjusted_score, risk_score, confidence, classification, recommendation.

### SARIF (`--format sarif`)
SARIF 2.1.0 for code scanning system integration. All rule descriptions include alternative explanations. Rules are informational — no security vulnerabilities claimed.

---

## Language support matrix

| Language | Heuristics | Framework | AST | Kotlin-native | Git | Status |
|---|---|---|---|---|---|---|
| **Python** | Full (34 signals) | FastAPI, Django, Flask, Pydantic, SQLAlchemy | Full (stdlib `ast`) | — | ✓ | **Full** |
| **Java** | Full (34 signals) | Spring Boot, JPA, Lombok, MapStruct, OpenAPI | Regex approximation¹ | — | ✓ | **Full** |
| **Kotlin** | Full (34 signals) | Spring Boot, JPA | Regex approximation¹ | ✓ Full | ✓ | **Full** |
| TypeScript | Partial (15 signals) | — | — | — | ✓ | Partial |
| JavaScript | Partial (15 signals) | — | — | — | ✓ | Partial |
| Vue | TypeScript signal set | — | — | — | ✓ | Partial |
| Go, Rust, C#, Ruby, PHP | Default (12 signals) | — | — | — | ✓ | Minimal |
| KotlinScript (.kts) | Kotlin signal set | — | — | ✓ | ✓ | Basic |

> ¹ **Java AST fallback**: Java uses regex brace-counting for method length estimation. A clean `JavaParserAdapter` interface exists for future integration with tree-sitter or javalang. When used, confidence is explicitly reduced and reported as "Java AST parser unavailable — using lexical approximation."

**Kotlin-specific**: data classes, sealed classes, coroutines, null-safety operators, and Android framework patterns are all given intentionally **low AI signals** — they are language idioms and framework conventions, not AI indicators.

---

## Architecture

```
scan repository
→ classify files (FileCategory) — before any scoring
→ detect framework context (Spring, JPA, Pydantic, Kotlin, Android...)
→ parse source (Python ast; Java regex; Kotlin regex)
→ extract signals:
    heuristic (34 signals) + lexical (entropy, TTR) + structural (AST/motifs)
    + scaffold completeness + magic number discipline + name-body coherence
    + style continuity + human irregularity + Kotlin-native + placeholder/LLM residue
    + test quality (for test files)
→ apply rules → raw_score
→ apply context adjustments (category × framework × criticality)
→ adjusted_score + risk_score
→ compute OriginEstimate (three-way: AI-like / AI-assisted / human-pattern)
    [skipped for GENERATED and VENDOR — tool-generated ≠ LLM-generated]
→ aggregate by file / module / category / repo
→ LOC-weighted portfolio_origin_estimate
→ produce reports (table / JSON v5.0 / Markdown / CSV / SARIF)
```

### Module structure

```
ai_pattern_analyzer/
├── __init__.py              — version 5.0.0
├── __main__.py              — CLI; --explain; --explain-repo; profiles
├── config.py                — 34 signal keys; language weights; GIT_BURST_HUMAN_KEYWORDS
├── config_file.py           — YAML/JSON config file loader
├── domain.py                — FileCategory; OriginEstimate; Finding; ScanConfig
├── _signal_metadata.py      — rule cards for all 34 signals
├── origin/
│   ├── engine.py            — OriginEstimateEngine; compute_file_origin(); aggregate()
│   └── confidence.py        — ConfidenceInterval; compute_interval(); portfolio_interval()
├── scanners/
│   ├── filesystem.py        — classify_file(); FileCategory; comprehensive vendor/generated
│   └── git.py               — get_commits(); import/migration keyword filtering
├── analyzers/
│   ├── heuristics.py        — 12 language-specific heuristics
│   ├── structural.py        — Python AST; Java structural approximation
│   ├── lexical.py           — token_entropy(); TTR; repetition_index()
│   ├── similarity.py        — TF-IDF cosine similarity
│   ├── git_signals.py       — burst (migration-filtered); diversity; message entropy
│   ├── framework.py         — Spring/JPA/Lombok/MapStruct/FastAPI/Pydantic/Django
│   ├── kotlin.py            — Kotlin-native: data class (low signal); coroutines; Android
│   ├── scaffold.py          — scaffold_completeness; magic_number_discipline; name_body_coherence
│   ├── style_continuity.py  — windowed style breaks; human_irregularity_score
│   ├── placeholder.py       — LLM residue; placeholder code; resilience theater
│   ├── test_quality.py      — assertion quality; mock abuse; fixture realism
│   └── pipeline.py          — multiprocessing-safe worker; all analyzers wired
├── scoring/
│   ├── model.py             — FileAnalysis v5.0; score_file(); origin_estimate skip for generated
│   ├── adjusted.py          — category/framework adjustments; risk score; uncertainty reasons
│   └── calibration.py       — RepoStats; ModuleSummary; origin_estimate aggregation
└── reporting/
    ├── cli.py               — terminal output; AI-Adoption Pattern Index; origin estimate
    ├── json_report.py       — JSON schema v5.0; portfolio_origin_estimate
    ├── markdown.py          — Markdown leadership report; pattern-signal labels
    └── sarif.py             — SARIF 2.1.0 stub
tests/
    ├── test_heuristics.py       — 29 tests
    ├── test_lexical.py          — 11 tests
    ├── test_framework.py        — 8 tests
    ├── test_scoring.py          — 19 tests
    ├── test_classification.py   — 10 tests
    ├── test_placeholder.py      — 11 tests
    ├── test_origin_estimate.py  — 29 tests (v5.0)
    ├── test_kotlin.py           — 14 tests (v5.0)
    ├── test_vendor_paths.py     — 20 tests (v5.0)
    ├── test_scaffold.py         — 19 tests (v5.0)
    └── test_wording_safety.py   — 17 tests (v5.0 — overclaiming and contamination)
```

---

## Comparison with industry tools

| Tool | AI-pattern signals | Code quality | Local-only | Origin estimate |
|---|---|---|---|---|
| **This tool** | ✓ Primary focus | ✓ Risk score, test quality | ✓ | ✓ Three-way (heuristic) |
| Sonar/SonarCloud | ✗ | ✓ Code smells, bugs, coverage | ✗ Cloud | ✗ |
| Semgrep | ✗ | ✓ Security, custom rules | ✓/✗ | ✗ |
| CodeQL | ✗ | ✓ Security, data flow | ✗ GitHub | ✗ |
| Ruff/Flake8/PMD | ✗ | ✓ Style, bugs | ✓ | ✗ |

This tool complements Sonar/Semgrep/Ruff — it adds the AI adoption dimension. Sonar output can be used as risk context (extension point).

---

## Ethics and anti-misuse

### What this tool must NOT be used for

- **Individual developer evaluation** — scores are not meaningful at the individual level
- **Disciplinary action** — no code pattern score constitutes grounds for personnel decisions
- **Contractual or legal claims** — scores are heuristic estimates, not evidence
- **Exact AI contribution measurement** — no tool can reliably measure this
- **Replacing engineering code review** — scores identify candidates, not conclusions
- **Surveillance of developers** — the developer fingerprint feature is disabled by default

### Anti-misuse guardrails built in

- `developer_fingerprint_enabled = false` by default; enabling requires explicit config
- Every origin estimate carries mandatory caveats
- `pct_note` warning embedded in every JSON origin estimate
- Generated/vendor files are excluded from origin estimates to prevent confusion between tool-generated and LLM-generated
- Summary labels use "pattern signal" language, not authorship language
- Report headers state "NOT a percentage of AI-generated files"

### Recommended use

- Repository-level AI adoption pattern index trends
- Team-level adoption proxy (aggregate, not individual)
- Changed-code monitoring in PRs
- Generated-code governance (detecting growing generated ratio)
- Manual review prioritization by risk score
- AI readiness analysis (which areas are low/high risk for AI-assisted development)

---

## Limitations

1. **Heuristic-only**: No ML, no semantic understanding, no real AST for Java
2. **Java AST**: Uses regex approximation; full JavaParser/tree-sitter integration is an extension point
3. **False positive rate**: Senior clean code, formatters, DTOs, framework code all appear AI-like
4. **False negative rate**: Edited AI code, Copilot completions, intentionally irregular AI code score low
5. **No ground truth**: Without labeled data from the same codebase, calibration is approximate
6. **Historical baseline**: Requires per-file git timestamps (extension point, not yet implemented)
7. **Recent-code analysis**: Requires git blame per file (extension point)
8. **Diff mode**: CLI flags exist; full implementation is an extension point
9. **Confidence intervals**: Heuristic width — not based on statistical sampling
10. **Single-file granularity**: Mixed-origin files score as aggregates

---

## Implementation status

See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for detailed status of all 83 v5.0 requirements plus 303 v4.0 requirements.

**Summary:** 52 fully implemented ✅ | 13 partially implemented 🔶 | 17 extension points 🔌

---

## Requirements

- **Python 3.8+** — standard library only for core analysis
- `git` CLI — for `--include-git` and `ci`/`full` profiles
- `pyyaml` (optional) — for YAML config file parsing; falls back to simple parser

### Docker / containerized scanning

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y git
COPY . /analyzer
WORKDIR /analyzer
```

```bash
docker run --rm -v /path/to/repo:/repo analyzer \
    python3 -m ai_pattern_analyzer --dirs /repo --profile ci --format json
```

No network access required. All analysis runs locally.

---

## Disclaimer

This tool detects **code pattern signals** using statistical heuristics. It does not identify authorship, prove AI usage, or constitute evidence for any contractual, compliance, legal, or personnel claim. Results are probabilistic pattern signals and should be interpreted as directional trend indicators only.

High AI-like pattern scores reflect stylistic and structural code characteristics — they are **not** a reliable measure of whether any specific code was generated by an AI system. Results must not be used to evaluate, discipline, or rank individual developers.
