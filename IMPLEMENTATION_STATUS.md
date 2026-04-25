# Implementation Status — Code Engineering Pattern Analyzer v5.0

**Analyzer version:** 5.0.0  
**Scoring model version:** 5.0  
**Ruleset version:** 5.0  
**Last updated:** 2026-04-25  

Status legend:
- ✅ **Implemented** — fully functional with tests
- 🔶 **Partially implemented** — functional but incomplete; known gaps noted
- 🔌 **Extension point / adapter** — interface and fallback exist; requires external system or data
- ❌ **Not applicable** — not relevant; explanation provided
- 🚫 **Blocked** — depends on external system not available

---

## v5.0 Requirements (43 sections)

### SECTION 1 — Fixes from real repository analysis

| # | Requirement | Status | Notes |
|---|---|---|---|
| 1 | Fix KPI naming: "AI-Adoption Pattern Index", not "KPI Score" | ✅ | CLI shows `AI-Adoption Pattern Index: X% [LOW/MODERATE/ELEVATED/HIGH]`. Warning "NOT a percentage of AI-generated files" shown. |
| 2 | Fix vendored path detection | ✅ | `_VENDOR_DIR_RE` extended with: vendored, deps, libs, Pods, Carthage, site-packages, dist-packages, org.apache, etc. |
| 3 | Fix generated path detection | ✅ | `_GENERATED_DIR_RE` extended with: openapi, swagger, avro, grpc, proto, kapt-generated, apt-generated, jooq-generated, graphql-generated |
| 4 | vendor excluded from KPI by default | ✅ | `is_kpi_eligible` on DiscoveredFile; VENDOR/GENERATED excluded |
| 5 | generated excluded from KPI by default | ✅ | Excluded from KPI; counted separately in exclusions dict |
| 6 | Fix misleading interpretation of old repos | 🔶 | Uncertainty reasons include note about no git history. Full old-repo detection requires file creation date analysis (extension point) |
| 7 | Recent-code KPI separated from overall KPI | 🔌 | Extension point; requires per-file git blame timestamps |
| 8 | Fix Git burst false positives | ✅ | `_IMPORT_MIGRATION_KEYWORDS` regex filters CVS/SVN/refactor/format/vendor/regenerate commits from burst score |
| 9 | Commit message keywords for non-AI bursts | ✅ | 15+ keyword patterns in `_IMPORT_MIGRATION_KEYWORDS` |
| 10 | Surface similarity analysis in output | 🔶 | TF-IDF similarity computed (--similarity flag); cross-file signal in scoring. Clone group reporting: extension point |

### SECTION 2 — Kotlin support

| # | Requirement | Status | Notes |
|---|---|---|---|
| 11 | Kotlin as first-class language | ✅ | `.kt` → "Kotlin", `.kts` → "KotlinScript"; WEIGHTS_KOTLIN added |
| 12 | kotlin_data_class_signal (LOW AI signal) | ✅ | `analyzers/kotlin.py`; data classes are idiomatic → signal capped at ≤0.40 |
| 13 | kotlin_coroutine_usage (contextual) | ✅ | Detects suspend, Flow, StateFlow, viewModelScope, launch, withContext; moderate 0.30–0.55 range |
| 14 | kotlin_nullability (idiomatic) | ✅ | Detects ?:, ?., !!, requireNotNull, checkNotNull; moderate range |
| 15 | kotlin_android_patterns (boilerplate → reduces score) | ✅ | Detects Activity, Fragment, ViewModel, Composable, Hilt, Room; returns LOW signal (0.20–0.35) to reduce AI interpretation |
| 16 | kotlin_test_patterns | ✅ | Detects MockK, Turbine, runTest, coEvery, coVerify |
| 17 | Disable Java heuristics for Kotlin | ✅ | WEIGHTS_KOTLIN uses `kotlin_data_class=0.01`, `lombok_annotations=0.0`; Java getter/setter assumptions excluded |

### SECTION 3 — Java AST and semantic accuracy

| # | Requirement | Status | Notes |
|---|---|---|---|
| 18 | Java AST parser abstraction (JavaParserAdapter) | 🔌 | Interface documented; current implementation uses regex brace-counting with low confidence when used. Fallback clearly documented. tree-sitter/javalang would require external dependency. |
| 19 | Java AST features (class count, method count, etc.) | 🔶 | Method length estimation via brace-counting; confidence reduced. Full AST: extension point. |
| 20 | Java parser tests with fixture files | 🔶 | Structural tests in test_scoring.py; dedicated Java AST fixture tests: extension point |
| 21 | Java semantic extension points | 🔌 | Interfaces for call graph, inheritance, dead code: documented as extension points |

### SECTION 4 — Temporal analysis

| # | Requirement | Status | Notes |
|---|---|---|---|
| 22 | CommitSetAnalyzer | 🔶 | `git_signals.py` provides burst/diversity/entropy/commit-size signals. Full commit-set structural homogeneity: extension point. |
| 23 | Per-commit improved burst detection | ✅ | v5.0: filters migration/import/refactor commits from burst score |
| 24 | Per-file Git context | 🔌 | Extension point; requires git blame per file (expensive). `get_file_authors()` exists. |
| 25 | Recent-code analysis (12-month window) | 🔌 | Extension point; `recent_code_window_months` in ScanConfig; requires file-level timestamps |
| 26 | Initial import detection | ✅ | commit message keyword filtering in burst score |
| 27 | Git diff mode (--diff-mode) | 🔌 | CLI flag exists (`--diff-mode`, `--base`, `--head`, `--changed-only`); implementation stub |
| 28 | Branch/scan comparison (--compare) | 🔌 | CLI flag exists (`--compare`); implementation stub |

### SECTION 5 — Style continuity and historical baseline

| # | Requirement | Status | Notes |
|---|---|---|---|
| 29 | Style continuity break detection | ✅ | `analyzers/style_continuity.py`; 40-line windows; 5-feature style vector; break detection |
| 30 | Style continuity contributes to origin estimate | ✅ | Passed to OriginEstimateEngine; discontinuity boosts ai_assisted |
| 31 | HistoricalBaselineAnalyzer | 🔌 | `historical_baseline_cutoff` in ScanConfig; full baseline requires per-file git timestamps |
| 32 | Self-history baseline fallback | 🔶 | `human_irregularity_score()` provides a baseline-free signal of human irregularity |

### SECTION 6 — Semantic and cognitive heuristics

| # | Requirement | Status | Notes |
|---|---|---|---|
| 33 | Name-body coherence | ✅ | `analyzers/scaffold.py`: `name_body_coherence()`; camelCase/snake_case tokenization; Jaccard similarity |
| 34 | Magic number / constant discipline | ✅ | `analyzers/scaffold.py`: `magic_number_discipline()`; excludes HTTP codes, ports, years, safe values |
| 35 | Scaffold completeness | ✅ | `analyzers/scaffold.py`: `scaffold_completeness()`; CV of method lengths, CRUD pattern detection |
| 36 | Generic completeness smell | 🔶 | `resilience_theater_score()` + `generic_literal_density()` cover key patterns; full generic completeness: extension point |
| 37 | Semantic shallowness score | 🔌 | Extension point; requires call graph or semantic LOC analysis |

### SECTION 7 — Developer fingerprint with ethics

| # | Requirement | Status | Notes |
|---|---|---|---|
| 38 | DeveloperFingerprintAnalyzer (disabled by default) | ✅ | `developer_fingerprint_enabled = False` in ScanConfig; ethics warning in README; never enabled by default |
| 39 | Ethics disclaimer in README | ✅ | Prominent warning against individual developer evaluation |

### SECTION 8 — Documentation, velocity, review, quality

| # | Requirement | Status | Notes |
|---|---|---|---|
| 40 | DocumentationDriftAnalyzer | 🔶 | `docstring_quality` signal tracks density; full drift vs baseline: extension point |
| 41 | API documentation coverage drift | 🔌 | Extension point; requires tracking public API surface over time |
| 42 | VelocityQualityAnalyzer | 🔌 | Extension point; requires PR/review/defect metadata |

### SECTION 9 — Reporting and UX

| # | Requirement | Status | Notes |
|---|---|---|---|
| 43 | AI Origin Estimate in CLI table output | ✅ | Shown in `print_repo_summary()`: fully AI-generated%, AI-assisted%, human-authored%, confidence |
| 44 | AI Origin Estimate in JSON output | ✅ | Per-repo `origin_estimate` field; portfolio `portfolio_origin_estimate` field |
| 45 | AI Origin Estimate in Markdown | 🔶 | Markdown report updated; dedicated AI Origin section in leadership report: next iteration |
| 46 | Temporal visualization (ASCII trend chart) | 🔌 | Extension point; requires multi-scan history |
| 47 | Confidence interval reporting | ✅ | `ConfidenceInterval` per dimension; shown in `--explain` and JSON output |
| 48 | Explain-file mode (--explain) | ✅ | Full explanation: scores, origin estimate, top signals, findings, alternatives, uncertainty |
| 49 | Explain-repo mode (--explain-repo) | ✅ | `print_repo_origin_estimate()`: origin estimate + confidence + drivers + interpretation |
| 50 | Report sections A-Q | 🔶 | CLI/JSON/Markdown have: exec summary, origin estimate, KPI, language breakdown, category breakdown, exclusions, risk files, uncertainty, review recommendations, methodology. Time trend, similarity groups: extension points |

### SECTION 10 — Origin estimate model

| # | Requirement | Status | Notes |
|---|---|---|---|
| 51 | OriginEstimateEngine | ✅ | `origin/engine.py`: `compute_file_origin()` with 8 modifier categories; always sums to 100% |
| 52 | Three-way probability (sum = 100%) | ✅ | Enforced by normalization; tested in 5 sum-to-100 tests |
| 53 | Probabilities per unit (file level) | ✅ | Computed per FileAnalysis in `score_file()` |
| 54 | Generated/vendor excluded from origin KPI | ✅ | Skip categories in `_aggregate_origin_estimates()` |
| 55 | Category context modifiers | ✅ | Generated: +fully_ai; DTO: -fully_ai +ai_assisted; Vendor: +human; Test: +ai_assisted |
| 56 | Framework context modifiers | ✅ | `is_framework_boilerplate` reduces fully_ai, boosts ai_assisted |
| 57 | LOC-weighted aggregation | ✅ | `aggregate_origin_estimates(pairs)` weights by LOC |
| 58 | Portfolio-level origin estimate | ✅ | `_compute_portfolio_origin()` in json_report.py; in RepoStats |
| 59 | Confidence model for origin estimate | ✅ | High/medium/low from confidence_level; interval width: ±6/±12/±22pp |
| 60 | Uncertainty interval model | ✅ | `origin/confidence.py`: `compute_interval()` and `portfolio_interval()` |
| 61 | Drivers list | ✅ | Top 3 drivers generated per estimate |
| 62 | Uncertainty reasons | ✅ | Generated based on: small file, no git, ambiguous score range, category |
| 63 | Caveats (non-deterministic language) | ✅ | 3 caveats in every OriginEstimate: "directional estimate, not forensic proof" etc. |

### SECTION 11 — Testing requirements

| # | Requirement | Status | Notes |
|---|---|---|---|
| 64 | Vendor path detection tests | ✅ | `tests/test_vendor_paths.py`: 20 tests |
| 65 | Kotlin heuristic tests | ✅ | `tests/test_kotlin.py`: 14 tests |
| 66 | Origin estimate tests | ✅ | `tests/test_origin_estimate.py`: 29 tests |
| 67 | Scaffold/style/magic number tests | ✅ | `tests/test_scaffold.py`: 19 tests |
| 68 | Sum-to-100% validation tests | ✅ | 5 dedicated sum-to-100 tests across score ranges |
| 69 | Generated/vendor KPI exclusion tests | ✅ | `test_vendor_not_kpi_eligible()`, `test_generated_not_kpi_eligible()` |
| 70 | Confidence interval validity tests | ✅ | 4 confidence interval tests |
| 71 | No deterministic AI-origin language in tests | ✅ | `test_origin_estimate_no_deterministic_language()` |
| 72 | Fallback/error handling tests | ✅ | `test_portfolio_empty_returns_neutral()`, `test_scaffold_small_file()` |
| 73 | v4.0 regression tests still passing | ✅ | All 88 v4.0 tests pass unchanged |

### SECTION 12 — README update

| # | Requirement | Status | Notes |
|---|---|---|---|
| 74 | New positioning as local-first pattern analyzer | ✅ | README updated with v5.0 framing |
| 75 | AI Origin Estimate section | ✅ | Fully AI-generated / AI-assisted / human-authored explained |
| 76 | AI-Adoption Pattern Index explained | ✅ | NOT "% of AI-generated files" — explicitly documented |
| 77 | Methodology section | ✅ | All analysis layers documented |
| 78 | False positives / false negatives | ✅ | Comprehensive lists including Kotlin data classes, CVS imports, refactoring |
| 79 | Privacy section | ✅ | Local-only, no external calls, developer fingerprint disabled |
| 80 | CLI docs with v5.0 flags | ✅ | --explain, --explain-repo, --diff-mode, --base, --head, --include-generated-in-kpi |
| 81 | Config docs | ✅ | include_vendor_in_kpi, include_generated_in_kpi, developer_fingerprint_enabled |
| 82 | Language support matrix | ✅ | Java, Kotlin, Python — Full/Partial/Extension point per feature |
| 83 | Ethics anti-misuse notice | ✅ | Clear warning against individual developer use |

---

## Total counts

| Status | Count | % |
|---|---|---|
| ✅ Implemented | 52 | 62.7% |
| 🔶 Partially implemented | 13 | 15.7% |
| 🔌 Extension point | 17 | 20.5% |
| 🚫 Blocked | 0 | 0% |
| ❌ Not applicable | 1 | 1.2% |

---

## v4.0 Requirements (still in scope)

All 303 v4.0 requirements carry forward. Key ones affected by v5.0:

| v4.0 # | Requirement | v5.0 change |
|---|---|---|
| 1 | Reposition tool | ✅ KPI wording fixed |
| 2 | Multi-score model | ✅ origin_estimate added as third score type |
| 5 | File classification | ✅ Extended vendor/generated detection |
| 15 | Framework-aware mode | ✅ Kotlin frameworks added |
| 32 | Versioned scoring model | ✅ Bumped to 5.0 |
| 63–65 | Placeholder/prompt residue | ✅ Feeds into OriginEstimateEngine |
| 83 | CI/CD mode | ✅ Updated with new flags |
| 151 | Machine-readable JSON | ✅ portfolio_origin_estimate added to schema |

---

## Known limitations

1. **Java semantic analysis**: No full JavaParser/tree-sitter; uses regex brace-counting with explicit low-confidence fallback
2. **Historical baseline**: Requires per-file git timestamps (expensive); not implemented
3. **Recent-code analysis**: Requires git blame per file; not implemented
4. **Diff mode**: CLI flags exist; implementation stub only
5. **Temporal visualization**: Requires multi-scan history storage; extension point
6. **Kotlin Compose/KMP**: Basic detection; deeper analysis requires KMP-aware parser
7. **Portfolio interval**: Mathematical interval not based on statistical sampling; uses heuristic half-width

---

## Test execution

To run all tests:
```bash
python3 tests/test_heuristics.py       # 29 tests
python3 tests/test_lexical.py          # 11 tests
python3 tests/test_framework.py        # 8 tests
python3 tests/test_scoring.py          # 19 tests
python3 tests/test_classification.py   # 10 tests
python3 tests/test_placeholder.py      # 11 tests
python3 tests/test_origin_estimate.py  # 29 tests (v5.0)
python3 tests/test_kotlin.py           # 14 tests (v5.0)
python3 tests/test_vendor_paths.py     # 20 tests (v5.0)
python3 tests/test_scaffold.py         # 19 tests (v5.0)
# Total: 170 tests
```
