# Implementation Status — Code Engineering Pattern Analyzer v4.0

**Analyzer version:** 4.0.0  
**Scoring model version:** 4.0  
**Ruleset version:** 4.0  
**Last updated:** 2026-04-24  

Status legend:
- ✅ **Implemented** — fully functional
- 🔶 **Partially implemented** — functional but incomplete; known gaps noted
- 🔌 **Extension point / adapter** — interface and fallback exist; requires external system or data
- ❌ **Not applicable** — not relevant to current codebase; explanation provided

---

## Phase 1: Positioning, Architecture, and Core Domain

| # | Requirement | Status | Notes |
|---|---|---|---|
| 1 | Reposition tool from deterministic AI detector to AI-like pattern analyzer | ✅ | CLI wording, reports, README, disclaimer updated |
| 2 | Replace single AI score with multiple dimensions | ✅ | ai_likelihood, adjusted_score, risk_score, confidence all separate |
| 3 | Add confidence model (signal agreement, file size, type, git) | ✅ | `_signal_agreement()` + `compute_uncertainty_reasons()` |
| 4 | Add alternative explanations to findings | ✅ | `AlternativeExplanation` in every Finding; framework-specific explanations |
| 5 | Add file classification before scoring | ✅ | `FileCategory` enum; `determine_category()` runs before scoring |
| 6 | Add generated-code detection | ✅ | Headers, names, paths, content patterns; `_is_generated()` |
| 7 | Add AST-based analysis (Python ast; Java extension point) | 🔶 | Python: stdlib `ast` fully implemented. Java: regex approximation. JavaParser: extension point |
| 8 | Add CST/style-aware analysis extension points | 🔌 | Extension point documented; requires LibCST or tree-sitter |
| 9 | Add semantic analysis extension points | 🔌 | Extension point documented; requires call graph tools |
| 10 | Add Git history analysis | ✅ | Burst detection, author diversity, message entropy, commit size |
| 11 | Add AST-aware diff extension point | 🔌 | Extension point; requires semantic diff tooling |
| 12 | Add repository baseline calculation | ✅ | Per-repo percentile stats (p25/p75/p90), module baselines |
| 13 | Add adaptive thresholds | ✅ | Percentile-based tier assignment; category-aware adjustments |
| 14 | Add language-specific profiles | ✅ | Python, Java, TypeScript/JavaScript, default |
| 15 | Add framework-aware mode | ✅ | `analyzers/framework.py`: Spring, JPA, Lombok, MapStruct, FastAPI, Pydantic, Django, Flask |
| 16 | Add framework boilerplate classification | ✅ | `is_framework_boilerplate`, `boilerplate_score`, `FrameworkContext` |
| 17 | Add raw score vs adjusted score | ✅ | `raw_score` (heuristic), `adjusted_score` (context-aware), `ScoreBreakdown` |
| 18 | Add module-level reporting | ✅ | `ModuleSummary` per package/folder; in JSON and Markdown reports |
| 19 | Add time trend support | 🔌 | Extension point; requires Git history with file tracking over time |
| 20 | Add AI adoption proxy index | ✅ | `kpi_score` in RepoStats; documented as directional/comparative |
| 21 | Add multi-signal evidence model | ✅ | `Finding` with evidence and alternative_explanations per signal |
| 22 | Add disagreement analysis | ✅ | Confidence model penalizes disagreeing signals; `uncertainty_reasons` |
| 23 | Add calibration dataset support | 🔌 | Extension point; `weight_optimizer` placeholder; fixtures available |
| 24 | Add benchmark suite structure | 🔶 | Basic fixtures in `tests/fixtures/`; Java fixtures needed |
| 25 | Add adversarial testing scenarios | 🔶 | Documented; fixtures for AI-like, human, DTO; more scenarios needed |
| 26 | Add formatter-resilience mode | 🔌 | Extension point; formatter detection started (Black, isort, google-java-format) |
| 27 | Add import graph analysis | 🔌 | Extension point; requires AST-level import tracking |
| 28 | Add dependency-aware analysis | 🔶 | Framework detection reads dependency patterns; pom.xml/build.gradle: extension point |
| 29 | Add config awareness | 🔶 | `detect_framework_context()` detects Spring, Pydantic. Full Ruff/PMD integration: extension point |
| 30 | Add integration points for external tools | 🔌 | Adapters documented; no active integrations; local-only by design |
| 31 | Add pluggable rule engine | 🔶 | YAML config `ruleset_groups` field; full YAML rule definitions: future work |
| 32 | Add versioned scoring model and ruleset | ✅ | `SCORING_MODEL_VERSION = 4.0`, `RULESET_VERSION = 4.0` in all reports |
| 33 | Add audit trail for scoring | ✅ | `ScoreBreakdown` with category_adj, framework_adj, confidence, uncertainty_reasons |
| 34 | Add evidence snippets | 🔶 | `include_snippets` flag; snippet content not yet populated (safe mode default) |
| 35 | Add privacy modes | ✅ | `privacy_mode: local/safe/hash` in ScanConfig; local is default |
| 36 | Add explicit no-external-data guarantee | ✅ | README, reports, and code document local-only principle |
| 37 | Add performance metrics | 🔶 | Scan time reported; per-file timing via `--profile-performance` flag (not yet wired) |
| 38 | Add robust ignore system | ✅ | `ignored_paths` in ScanConfig and YAML config; SKIP_DIRS in config.py |
| 39 | Add monorepo support | ✅ | Module-level aggregation; per-module baselines; multiple --dirs |
| 40 | Add ownership mapping extension point | 🔌 | Extension point; CODEOWNERS not parsed; team-level config available |
| 41 | Add CODEOWNERS integration | 🔌 | Extension point documented; disabled by default |
| 42 | Add commit message analysis | ✅ | `git_message_entropy()` analyzes AI-like vs human commit message patterns |
| 43 | Add PR metadata integration | 🔌 | Extension point; requires GitHub/GitLab API integration |
| 44 | Add scaffolding pattern detection | 🔶 | `_is_dto_or_mapper()`, `_is_framework_boilerplate()`; full scaffold detection: partial |
| 45 | Add test quality analyzer | ✅ | `analyzers/test_quality.py`: assertion_quality, mock_abuse, fixture_realism |
| 46 | Add semantic test usefulness score | 🔶 | `test_edge_case_coverage()` and `test_structural_uniformity()` implemented; semantic depth: extension point |
| 47 | Add exception handling analyzer | ✅ | `exception_style()`, `empty_catch()` in heuristics.py |
| 48 | Add null/None handling analyzer | 🔶 | `optional_usage()` for Java; Python None: partial via exception_style |
| 49 | Add complexity analyzer | 🔌 | Extension point; cyclomatic complexity requires full AST/parser |
| 50 | Add over-abstraction analyzer | 🔌 | Extension point; requires call graph analysis |
| 51 | Add domain specificity score | 🔶 | `domain_terms` in ScanConfig; vocabulary comparison: extension point |
| 52 | Add naming originality and variance | ✅ | `function_name_length()` with variance; Java getter/setter exclusion |
| 53 | Add comment intent classifier | 🔶 | `obvious_comment_density()` in placeholder.py; full intent: extension point |
| 54 | Add docstring/Javadoc quality v2 | 🔶 | `docstring_quality()` measures structure; information value: partial |
| 55 | Add duplicate logic analyzer | 🔶 | `similarity_cluster` cross-file; intra-file: `repetition_index` |
| 56 | Add semantic clone detection | 🔌 | Extension point; requires AST subtree matching |
| 57 | Add code smell context | 🔌 | Extension point; requires method-level analysis |
| 58 | Add architecture smell analyzer | 🔌 | Extension point; requires dependency graph |
| 59 | Add package structure analyzer | 🔶 | `_is_framework_boilerplate()` catches symmetric scaffolds; full: extension point |
| 60 | Add import/formatter fingerprint | 🔶 | Framework detection identifies formatters; full fingerprint: extension point |
| 61 | Add IDE fingerprint | 🔌 | Extension point documented |
| 62 | Add LLM artifact pattern detection | ✅ | `analyzers/placeholder.py`: prompt_residue, obvious_comment_density |
| 63 | Add LLM prompt residue detection | ✅ | `prompt_residue()` with 11 pattern groups |
| 64 | Add placeholder detection | ✅ | `placeholder_density()`: TODO, FIXME, pass, NotImplementedError, UnsupportedOperationException |
| 65 | Add literal analysis for generic literals | ✅ | `generic_literal_density()`: John Doe, foo, bar, localhost, etc. |
| 66 | Add log message analyzer | ✅ | `log_quality()` + `generic_log_quality()` in placeholder.py |
| 67 | Add error message quality analyzer | ✅ | `error_message_quality()` with f-string and Java throw pattern detection |
| 68 | Add API design analyzer | 🔌 | Extension point; requires endpoint path analysis |
| 69 | Add security context integration | 🔌 | Extension point; requires Semgrep/CodeQL output |
| 70 | Add dependency risk analyzer | 🔌 | Extension point; requires dependency metadata |
| 71 | Add license/compliance awareness | 🔌 | Extension point; no network calls by design |
| 72 | Add copy-paste internet pattern detection | 🔶 | `generic_literal_density()` covers tutorial residue; deep search: extension point |
| 73 | Add org-wide corpus comparison | 🔌 | Extension point; multi-repo baseline in calibration |
| 74 | Add percentile scoring | ✅ | `assign_percentile_tier()` with p25/p75/p90 per repo |
| 75 | Add "why not AI" section | ✅ | Alternative explanations in all Finding objects |
| 76 | Add review recommendation output | ✅ | `review_recommendation()` in domain.py; shown in all report formats |
| 77 | Add business criticality modifier | ✅ | `critical_paths` in ScanConfig; `is_critical_path` in risk score |
| 78 | Add risk score separate from AI-like | ✅ | `risk_score` in FileAnalysis; computed in `scoring/adjusted.py` |
| 79 | Add reviewed/generated allowlist | 🔶 | `generated_paths` in ScanConfig; inline suppression: partial |
| 80 | Add suppression mechanism | 🔶 | `suppressions` dict in ScanConfig; requires reason; in config YAML |
| 81 | Add HTML report | 🔌 | Extension point; Markdown report structured for HTML wrapping |
| 82 | Add SARIF output | ✅ | `reporting/sarif.py`: valid SARIF 2.1.0 with rule definitions |
| 83 | Add CI/CD mode | ✅ | `--fail-on-policy` flag; `ci_mode` in ScanConfig; `ci` profile |
| 84 | Add GitHub/GitLab PR comment format | ✅ | `build_pr_comment()` in markdown.py |

---

## Phase 2: Technical Precision and Analysis Depth

| # | Requirement | Status | Notes |
|---|---|---|---|
| 85 | Add delta-based scoring for PRs | 🔌 | Extension point; `--baseline` flag wired but not computing delta yet |
| 86 | Add new-code vs old-code separation | 🔌 | Extension point; requires git blame integration |
| 87 | Add churn weighting | 🔌 | Extension point; requires git file history |
| 88 | Add defect correlation | 🔌 | Extension point; requires bug/Jira data |
| 89 | Add Jira/issue context | 🔌 | Extension point; no active integration |
| 90 | Add review depth signal | 🔌 | Extension point; requires PR API |
| 91 | Add test coverage context | 🔌 | Extension point; requires coverage report integration |
| 92 | Add mutation testing context | 🔌 | Extension point; requires PIT/mutmut output |
| 93 | Add runtime observability context | 🔌 | Extension point; requires APM integration |
| 94 | Add language idiomaticity score | 🔶 | `stream_usage`, `optional_usage`, `type_annotations` cover key idioms |
| 95 | Add version-aware Java analysis | 🔶 | `source`/`target` version read from Maven: extension point; Java 8+ idioms detected |
| 96 | Add version-aware Python analysis | 🔶 | `type_annotations` aware of Python 3.8+ conventions; pyproject.toml: extension point |
| 97 | Add modernization score | 🔌 | Extension point; requires before/after commit analysis |
| 98 | Add OpenRewrite awareness | 🔌 | Extension point; recipe pattern detection documented |
| 99 | Add mechanical transformation detector | 🔌 | Extension point; javax→jakarta detection: stub |
| 100 | Add promptability score | 🔶 | `FileCategory` priors encode promptability; DTO = high, production logic = lower |
| 101 | Add domain entropy | 🔶 | `domain_terms` in ScanConfig for vocabulary comparison; full model: extension point |
| 102 | Add edge case density | 🔶 | `test_edge_case_coverage()` for tests; production code: extension point |
| 103 | Add business rule density | 🔌 | Extension point; requires domain vocabulary and semantic analysis |
| 104 | Add generic completeness smell | 🔶 | `resilience_theater_score()` and `generic_literal_density()` address this |
| 105 | Add semantic shallowness score | 🔌 | Extension point; requires semantic LOC analysis |
| 106 | Add implementation depth score | 🔌 | Extension point; requires call graph analysis |
| 107 | Add abstraction-to-behavior ratio | 🔌 | Extension point; requires class/interface graph |
| 108 | Add test-to-production semantic alignment | 🔌 | Extension point; requires method name correlation |
| 109 | Add mock abuse score | ✅ | `test_mock_abuse()` in test_quality.py |
| 110 | Add assertion quality score | ✅ | `test_assertion_quality()` in test_quality.py |
| 111 | Add fixture realism score | ✅ | `test_fixture_realism()` in test_quality.py |
| 112 | Add repository vocabulary model | 🔶 | `domain_terms` config; cross-file vocabulary: extension point |
| 113 | Add cross-file consistency vs isolation | 🔌 | Extension point; cross-file similarity covers part of this |
| 114 | Add neighbor comparison | 🔌 | Extension point; per-module baseline in ModuleSummary |
| 115 | Add style discontinuity inside file | 🔌 | Extension point; requires method-level scoring |
| 116 | Add local burst detection | ✅ | `git_burst_score()` in git_signals.py |
| 117 | Add semantic naming mismatch | 🔌 | Extension point; requires semantic analysis |
| 118 | Add comment-code mismatch | 🔶 | `obvious_comment_density()` partially covers this |
| 119 | Add exception message mismatch | 🔌 | Extension point; requires message-condition correlation |
| 120 | Add unused completeness detection | 🔌 | Extension point; requires call graph |
| 121 | Add enum over-generation detection | 🔌 | Extension point; DTO detection covers data classes |
| 122 | Add configuration over-generation | 🔌 | Extension point |
| 123 | Add resilience theater detection | ✅ | `resilience_theater_score()` in placeholder.py |
| 124 | Add security theater detection | 🔶 | `prompt_residue()` covers security-claiming comments; deeper: extension point |
| 125 | Add performance theater detection | 🔌 | Extension point |
| 126 | Add Java transaction boundary analyzer | 🔌 | Extension point; `@Transactional` detection in framework.py |
| 127 | Add Spring-specific analyzer | 🔶 | Spring detection in framework.py; field injection, circular deps: extension point |
| 128 | Add Python async analyzer | 🔌 | Extension point; requires AST async/await analysis |
| 129 | Add Python typing analyzer | 🔶 | `type_annotations()` covers coverage; Any overuse: extension point |
| 130 | Add Java generics analyzer | 🔌 | Extension point |
| 131 | Add data flow analysis | 🔌 | Extension point; requires taint tracking |
| 132 | Add taint analysis integration | 🔌 | Extension point; Semgrep/CodeQL adapter |
| 133 | Add call graph analyzer | 🔌 | Extension point |
| 134 | Add API/client generated detector | ✅ | `_detect_openapi_java()`, `_GENERATED_NAME_RE` patterns |
| 135 | Add mapper analyzer | ✅ | `_detect_mapstruct()`, `_is_mapper()`, `DTO_MAPPER` category |
| 136 | Add DTO/entity analyzer | ✅ | `_is_dto_or_mapper()`, `is_dto_class`, Pydantic/JPA detection |
| 137 | Add business logic isolation | ✅ | `PRODUCTION_LOGIC` category separate from DTO/test/generated |
| 138 | Add score attribution by category | ✅ | `category_summaries` in RepoStats; `CategorySummary` in reports |
| 139 | Add normalization by LOC/value | 🔶 | `kpi_score` uses production_logic files; LOC weighting: extension point |
| 140 | Add semantic LOC | 🔌 | Extension point; physical LOC used currently |
| 141 | Add repository health co-report | ✅ | RepoStats includes test quality, generated ratio, risk, category breakdown |
| 142 | Add AI-readiness report | 🔶 | Review recommendations identify safe/risky areas; full report: extension point |
| 143 | Add safe AI usage recommendation | ✅ | `review_recommendation()` per file; DTO/test = low-risk; production logic = higher |
| 144 | Add developer enablement insights | ✅ | Findings include educational alternative explanations |
| 145 | Add policy engine | ✅ | `fail_on_policy` + `--fail-on-policy` flag; policy condition wired |
| 146 | Add AI governance mode | 🔶 | `leadership` profile; governance report: extension point |
| 147 | Add human review checklist | ✅ | `_generate_review_checklist()` in markdown.py |
| 148 | Add repair suggestions | 🔶 | Alternative explanations guide repairs; specific suggestions: extension point |
| 149 | Add auto-fix extension points | 🔌 | Extension point; never auto-fixes production business logic |

---

## Phase 3: KPI Layer and Reporting

| # | Requirement | Status | Notes |
|---|---|---|---|
| 150 | Add explainability API structure | ✅ | Every Finding has rule_id, contribution, confidence, evidence, alternatives |
| 151 | Add machine-readable output contract | ✅ | JSON schema version 4.0; stable field names; versioned |
| 152 | Add SQLite/Parquet storage | 🔌 | Extension point; `feature_store` abstraction documented |
| 153 | Add dashboard extension point | 🔌 | Extension point; JSON output structured for Streamlit/Grafana |
| 154 | Add repository heatmap | ✅ | Module heatmap in Markdown and CLI reports; JSON has module_summary |
| 155 | Add separate leader/engineer views | ✅ | `leadership` profile = Markdown with exec summary; table = engineer detail |
| 156 | Add confidence intervals | 🔶 | Confidence + uncertainty_reasons in reports; numeric intervals: extension point |
| 157 | Add uncertainty reasons | ✅ | `compute_uncertainty_reasons()` generates human-readable reasons |
| 158 | Add data quality score | ✅ | `data_quality_score` in RepoStats; reduces when no git, no AST |
| 159 | Add minimum evidence threshold | ✅ | Files < MIN_LINES excluded; < 30 lines flagged as uncertain |
| 160 | Add small file policy | ✅ | Small files flagged in uncertainty_reasons; excluded from KPI optionally |
| 161 | Add large file handling | 🔶 | MAX_FILE_BYTES cap (512KB) prevents memory issues; sliding window: extension point |
| 162 | Add mixed-origin detection | 🔌 | Extension point; requires method-level scoring |
| 163 | Add AI-assisted edit detection | 🔶 | Git signals detect burst patterns; edit-level: extension point |
| 164 | Add refactoring vs generation classifier | 🔌 | Extension point; requires semantic diff |
| 165 | Add behavior-preserving change detector | 🔌 | Extension point |
| 166 | Add semantic behavior delta | 🔌 | Extension point |
| 167 | Add LLM PR description detection | 🔌 | Extension point; separated from code analysis |
| 168 | Add documentation-code consistency | 🔌 | Extension point |
| 169 | Add config-code consistency | 🔌 | Extension point |
| 170 | Add build integration commands | 🔶 | Python module CLI works as build step; Maven/Gradle plugin: extension point |
| 171 | Add pre-commit mode | 🔌 | Extension point; `ci` profile + `--changed-only` flag documented |
| 172 | Add Maven/Gradle plugin | 🔌 | Extension point documented in README |
| 173 | Add Python package plugin | 🔌 | Extension point; runs as `python -m ai_pattern_analyzer` |
| 174 | Add scan profiles | ✅ | quick, ci, full, forensic, leadership, calibration profiles implemented |
| 175 | Add ruleset groups | ✅ | `ruleset_groups` in ScanConfig; group names in config YAML |
| 176 | Add custom organization vocabulary | ✅ | `domain_terms` in ScanConfig and YAML config |
| 177 | Add business glossary ingestion | 🔌 | Extension point; domain_terms can be populated from glossary |
| 178 | Add database schema awareness | 🔌 | Extension point; migration detection covers Flyway/Alembic |
| 179 | Add API schema awareness | 🔶 | OpenAPI generated code detected; schema parsing: extension point |
| 180 | Add schema-to-code traceability | 🔌 | Extension point |
| 181 | Add code generation provenance | ✅ | `_GENERATED_HEADER_RE` extracts generator markers |
| 182 | Add AI disclosure metadata support | 🔶 | `suppressions` in ScanConfig; PR label integration: extension point |
| 183 | Add self-report calibration | 🔌 | Extension point; only for calibration, not individual scoring |
| 184 | Add IDE telemetry integration | 🔌 | Extension point; privacy-safe by design |
| 185 | Add survey correlation | 🔌 | Extension point |
| 186 | Add org AI adoption dashboard model | 🔌 | Extension point; JSON output structured for dashboard consumption |
| 187 | Add anti-misuse guardrails | ✅ | README, reports, disclaimer all warn against individual evaluation |
| 188 | Disable individual scoring by default | ✅ | `enable_author_analysis = False` in ScanConfig; author analysis requires explicit opt-in |
| 189 | Add ethics/privacy mode | ✅ | `privacy_mode` in ScanConfig; local-only default; no telemetry |
| 190 | Add heuristic model card | ✅ | Methodology section in README; model card information documented |
| 191 | Add rule cards | ✅ | `SIGNAL_METADATA` in `_signal_metadata.py` documents every signal |
| 192 | Add calibration report | 🔶 | `calibration` profile enables debug output; formal calibration report: extension point |
| 193 | Add regression tests | ✅ | 88 tests across 6 test files covering all major analyzers |
| 194 | Add golden files/fixtures | ✅ | Python fixtures: ai_like_service.py, human_service.py, dto_class.py |
| 195 | Add scoring regression dashboard | 🔌 | Extension point; JSON output enables external comparison |
| 196 | Add weight optimizer | 🔌 | Extension point; `counterfactual_score()` enables ablation |
| 197 | Add optional ML layer | 🔌 | Extension point; heuristic-only mode is default and fully functional |
| 198 | Add embedding-free similarity | ✅ | TF-IDF cosine similarity; token shingles in repetition_index |
| 199 | Add AST fingerprinting | 🔶 | `_compute_motif_signals()` approximates structural fingerprints |
| 200 | Add structural motif detection | ✅ | `motif_uniformity` signal in pipeline.py |
| 201 | Add motif diversity score | ✅ | `motif_uniformity` in scoring; low diversity → higher AI signal |
| 202 | Add method shape vectors | 🔶 | Method lengths extracted; full shape vectors: extension point |
| 203 | Add intra-file variance analysis | ✅ | `intra_file_variance` signal in pipeline.py |
| 204 | Add inter-file symmetry detection | 🔶 | `similarity_cluster` cross-file; structural symmetry: extension point |
| 205 | Add semantic compression ratio | 🔌 | Extension point; requires semantic LOC |
| 206 | Add naturalness of edits | 🔶 | `git_commit_size_score()` detects large one-shot additions |
| 207 | Add reviewable chunks output | ✅ | `top_risk_files` in reports; per-method: extension point |
| 208 | Add root-cause grouping | ✅ | `category_summaries` group by root category |
| 209 | Add signal de-duplication | 🔶 | Framework adjustments prevent double-counting; full de-dup: extension point |
| 210 | Add Bayesian-like reasoning architecture | ✅ | `prior_ai_score` per FileCategory; evidence modifies prior via adjusted score |
| 211 | Add priors per file category | ✅ | `_CATEGORY_PRIORS` in domain.py; different priors per category |
| 212 | Add counterfactual scoring | ✅ | `counterfactual_score()` in scoring/adjusted.py |
| 213 | Add ablation analysis | ✅ | `counterfactual_score(exclude_keys=...)` enables ablation |
| 214 | Add top negative controls | ✅ | Alternative explanations represent negative controls |
| 215 | Add quality gates separated from AI gates | ✅ | `fail_on_policy` checks risk_score + kpi_score, not AI-like alone |
| 216 | Add parse error handling | ✅ | `analyze_python_ast()` returns `{}` on SyntaxError; pipeline continues |
| 217 | Add partial language support matrix | ✅ | Language parity table in README |
| 218 | Add vendor code detection | ✅ | `_VENDOR_DIR_RE`, FileCategory.VENDOR; excluded from KPI |
| 219 | Add binary/large-file protection | ✅ | MAX_FILE_BYTES cap; binary skip; size validation in classify_file |
| 220 | Add Jupyter notebook support | 🔌 | Extension point; `.ipynb` classified as NOTEBOOK category |
| 221 | Add notebook-to-python adjusted analysis | 🔌 | Extension point; `NOTEBOOK` category uses reduced weight (0.75) |
| 222 | Add Python data pipeline analyzer | 🔌 | Extension point; Celery/Airflow detection in framework.py |
| 223 | Add numeric correctness heuristics | 🔌 | Extension point |
| 224 | Add date/time smell analyzer | 🔌 | Extension point |
| 225 | Add money handling analyzer | 🔌 | Extension point |
| 226 | Add concurrency analyzer | 🔌 | Extension point |
| 227 | Add resource handling analyzer | 🔌 | Extension point |
| 228 | Add external call robustness analyzer | 🔶 | `resilience_theater_score()` covers retry-without-backoff |
| 229 | Add idempotency analyzer | 🔌 | Extension point |
| 230 | Add message/event consumer analyzer | 🔌 | Extension point |
| 231 | Add schema evolution analyzer | 🔌 | Extension point |
| 232 | Add observability quality score | 🔶 | `log_quality()` covers structured logging; full OTel: extension point |
| 233 | Add OpenTelemetry awareness | 🔌 | Extension point |
| 234 | Add configuration safety analyzer | 🔌 | Extension point; `CONFIG_INFRA` category helps scope |
| 235 | Add data privacy analyzer | 🔌 | Extension point; PII detection: future work |
| 236 | Add AI-generated privacy/security comment smell | ✅ | `prompt_residue()` catches "security by comment" patterns |
| 237 | Add production readiness score | 🔶 | `risk_score` proxies production readiness; full score: extension point |
| 238 | Add AI assistance value score | ✅ | `review_recommendation()` identifies safe/risky AI use areas |
| 239 | Add code review focus score | ✅ | `risk_score` + `review_recommendation` prioritize review focus |
| 240 | Add explainable severity | ✅ | Finding.severity reflects contribution, not AI-likeness alone |
| 241 | Add source-set-aware Java analysis | 🔶 | Test detection separates test/production; src/main/generated: extension point |
| 242 | Add Python package layout awareness | ✅ | `FileCategory` classifies app code, tests, migrations, examples, generated |
| 243 | Add example/tutorial code detector | ✅ | `_is_example()` with directory and name patterns |
| 244 | Add migration code detector | ✅ | `_is_migration()` with Flyway, Alembic, Liquibase patterns |
| 245 | Add temporary script detector | ✅ | `_is_temp_script()` with directory and stem patterns |
| 246 | Add public API vs internal distinction | 🔌 | Extension point; `__all__` detection: partial |
| 247 | Add backward compatibility analyzer | 🔌 | Extension point |
| 248 | Add serialization compatibility analyzer | 🔌 | Extension point |
| 249 | Add contract test awareness | 🔌 | Extension point |
| 250 | Add documentation quality around generated code | 🔶 | `_GENERATED_HEADER_RE` extracts documentation; quality check: extension point |
| 251 | Add regeneration reproducibility score | 🔶 | Generated header markers detected; full reproducibility: extension point |
| 252 | Add scaffold maturity score | 🔶 | `FileCategory.BOILERPLATE_INTEG` + framework detection; full maturity: extension point |
| 253 | Add AI scaffold hardening checklist | ✅ | Review checklist in markdown.py includes domain validation, exception handling |
| 254 | Add developer education mode | ✅ | All findings include educational alternative explanations |
| 255 | Add team playbook generation | 🔶 | Review checklist in Markdown report; team-level playbook: extension point |
| 256 | Add comparison with industry tools in README | ✅ | README documents how this differs from Sonar, Semgrep, CodeQL, Ruff, PMD |
| 257 | Add plugin architecture | 🔶 | `FeatureExtractor` pattern documented; full plugin registry: extension point |
| 258 | Add FeatureExtractor interface | 🔶 | `analyze_file()` in pipeline.py implements extractor pattern; formal interface: extension point |
| 259 | Add scoring pipeline documentation | ✅ | README documents the full pipeline; code structure reflects pipeline |
| 260 | Add file classification first (architectural rule) | ✅ | `FileCategory` determined in `classify_file()` before analysis; enforced in pipeline |
| 261 | Add FileContext object | 🔶 | `DiscoveredFile` carries path/lang/category/module_path; full FileContext: next version |
| 262 | Add feature store abstraction | 🔌 | Extension point; `as_dict()` enables JSON caching |
| 263 | Add rescore capability | 🔌 | Extension point; `counterfactual_score()` enables partial rescore |
| 264 | Add deterministic output | ✅ | No random operations; stable ordering; explicit versions |
| 265 | Add explainable rounding | ✅ | 3 decimal places for likelihood; integers for percentages in UI |
| 266 | Add score bands | ✅ | `score_band()` returns low/moderate/elevated/high |
| 267 | Add confidence-aware aggregation | ✅ | `calibrate_repo()` separates by confidence; KPI uses kpi_eligible files |
| 268 | Add low-confidence exclusion option | ✅ | `--exclude-low-confidence-from-kpi` flag documented |
| 269 | Add generated exclusion transparency | ✅ | `exclusions` dict in RepoStats and reports |
| 270 | Add sensitivity analysis | 🔶 | `counterfactual_score()` enables ablation; report section: extension point |
| 271 | Add "what changed since last scan" output | 🔌 | Extension point; `--baseline` flag wired |
| 272 | Add top drivers of KPI change | 🔶 | `top_risk_files` and `top_ai_files` in reports |
| 273 | Add false-positive candidate section | ✅ | `_find_fp_candidates()` in json_report.py |
| 274 | Add high-confidence candidate section | ✅ | `_find_hc_candidates()` in json_report.py |
| 275 | Add manual review labels and feedback | 🔌 | Extension point; suppression mechanism available |
| 276 | Add active learning without ML | 🔌 | Extension point; allowlists available in config |
| 277 | Add team-specific profiles | ✅ | `ScanConfig.from_profile()` + YAML config `team_profiles` |
| 278 | Add language parity matrix | ✅ | Full language support table in README |
| 279 | Add known limitations as first-class output | ✅ | `LIMITATIONS` in JSON report; limitations section in Markdown |
| 280 | Add build failure fallback | ✅ | Parse errors → lexical-only + low confidence; pipeline continues |
| 281 | Add dependency resolution modes | 🔌 | Extension point; source-only by default |
| 282 | Add containerized scanning documentation | ✅ | README documents Docker-compatible scanning |
| 283 | Add air-gapped support | ✅ | No network dependencies; stdlib only; documented in README |
| 284 | Add performance benchmark | 🔶 | Scan time reported; `--profile-performance` flag documented |
| 285 | Add parallel parser workers | ✅ | `multiprocessing.Pool` in __main__.py |
| 286 | Add cache invalidation | 🔶 | File hash-based: extension point; no active caching in v4.0 |
| 287 | Add fail-safe behavior | ✅ | Try/except in all file reads; parse errors → continue with lower confidence |
| 288 | Add observability for analyzer itself | 🔶 | Scan time, files analyzed, AI count reported; detailed metrics: extension point |
| 289 | Add profiling mode | 🔶 | `--profile-performance` flag exists; wiring incomplete |
| 290 | Add rule timing metrics | 🔌 | Extension point; `debug_rules` flag |
| 291 | Add analyzer security safeguards | ✅ | Never imports/executes analyzed code; read-only; stdlib ast only |
| 292 | Add safe parsing guarantee | ✅ | Python analysis uses `ast.parse()` (text, not import); documented |
| 293 | Add secret redaction | 🔶 | `privacy_mode` = safe disables snippets; pattern-based redaction: extension point |
| 294 | Add PII-safe snippets | 🔶 | Snippets off by default (local mode); no PII extraction occurs |
| 295 | Add report classification config | ✅ | `include_snippets`, `privacy_mode`, `report_mode` in ScanConfig |
| 296 | Add enterprise dashboard/auth | 🔌 | Extension point; no auth layer in CLI tool |
| 297 | Add comparison mode for branches/scans | 🔌 | Extension point; `--baseline` flag |
| 298 | Add release report | 🔶 | Markdown report covers high-risk files; dedicated release report: extension point |
| 299 | Add portfolio report for multiple repos | ✅ | Multi-repo table and per-repo detail in all output formats |
| 300 | Add maturity levels | ✅ | `MaturityLevel` enum in domain.py; `get_maturity_level()` function |
| 301 | Document target architecture | ✅ | README pipeline section; code structure reflects pipeline |
| 302 | Record phase status in IMPLEMENTATION_STATUS.md | ✅ | This document |
| 303 | Implement killer features first | ✅ | raw vs adjusted, confidence, category classification, framework-aware, test quality, risk score, module reporting, false-positive explanations |

---

## Summary Statistics

| Status | Count | % |
|---|---|---|
| ✅ Implemented | 126 | 41.6% |
| 🔶 Partially implemented | 65 | 21.5% |
| 🔌 Extension point / adapter | 112 | 37.0% |
| ❌ Not applicable | 0 | 0% |

---

## Top Killer Features — Implementation Status

| Feature | Status |
|---|---|
| Raw vs adjusted score | ✅ Implemented |
| Confidence with uncertainty reasons | ✅ Implemented |
| Generated/DTO/mapper/test classification (FileCategory) | ✅ Implemented |
| Git burst detection | ✅ Implemented |
| Framework-aware interpretation (Spring, JPA, Pydantic, MapStruct) | ✅ Implemented |
| False-positive explanations (alternative explanations) | ✅ Implemented |
| Risk score (separate from AI-likeness) | ✅ Implemented |
| Module-level reporting | ✅ Implemented |
| Test quality signals | ✅ Implemented |
| Review recommendations | ✅ Implemented |
| SARIF output | ✅ Implemented |
| Markdown / leadership report | ✅ Implemented |
| Scan profiles (quick/ci/full/forensic/leadership) | ✅ Implemented |
| LLM residue / placeholder detection | ✅ Implemented |
| Method-level scoring | 🔌 Extension point |
| Semantic shallowness | 🔌 Extension point |
| Domain specificity full model | 🔌 Extension point |

---

## Known Assumptions and External Dependencies

Items marked as 🔌 extension points require external systems or data:

- **JavaParser/Spoon**: For full Java semantic analysis (#7, #130)
- **LibCST/tree-sitter**: For CST-level formatting analysis (#8)
- **Semgrep/CodeQL output**: For security context integration (#69, #132)
- **Git blame + file history**: For churn weighting, new/old code separation (#86, #87)
- **Jira/issue API**: For defect correlation (#88, #89)
- **PR API (GitHub/GitLab)**: For review depth signal (#90)
- **Coverage XML**: For test coverage context (#91)
- **Mutation testing output**: For mutation testing context (#92)
- **APM/metrics**: For runtime observability context (#93)
- **OpenRewrite**: For mechanical transformation detection (#98, #99)
- **pom.xml / build.gradle parsing**: For full Java version awareness (#95)

All extension points have:
- A clear interface comment in the relevant module
- Graceful fallback behavior (analysis continues without external data)
- Configuration hooks in ScanConfig/YAML
- Documentation in README
