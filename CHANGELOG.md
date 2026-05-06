# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [5.0.1] — 2026-05-06

### Added
- `LICENSE` (MIT)
- `CONTRIBUTING.md` — contribution guidelines and dev setup
- `SECURITY.md` — threat model and vulnerability reporting policy
- `CODE_OF_CONDUCT.md`
- `ARCHITECTURE.md` — high-level pipeline and design principles
- `CHANGELOG.md` (this file)
- `.github/workflows/ci.yml` — matrix testing on Python 3.8/3.10/3.12 + analyzer self-scan
- `.github/ISSUE_TEMPLATE/` — bug report, feature request, security routing
- `.github/PULL_REQUEST_TEMPLATE.md`
- README badges: CI status, Python version, License, Tests, Local-first, Languages, Schema

### Note
- No behavior changes. Open-source-readiness release.

## [5.0.0] — 2026-04-25

### Added
- **Three-way AI Origin Pattern Estimate** per file and per repository (fully AI-like / AI-assisted / human-pattern), always summing to 100%
- `origin/engine.py` — `OriginEstimateEngine` with 8 modifier categories
- `origin/confidence.py` — `ConfidenceInterval`, `compute_interval()`, `portfolio_interval()`
- `--explain FILE` mode — full per-file explanation: scores, origin estimate, top signals, alternatives, uncertainty
- `--explain-repo` mode — repository-level Origin Pattern Estimate with drivers and interpretation
- **Kotlin as first-class language** — 34 signals; data class given LOW signal (idiomatic, not AI); coroutines, nullability, Android patterns
- **Scaffold completeness** analyzer — method length CV, CRUD pattern detection
- **Magic number discipline** signal — excludes safe values (HTTP codes, ports, years)
- **Name-body coherence** signal — function name vs. implementation alignment via Jaccard similarity
- **Style continuity break detection** — 40-line windows, 5-feature style vector
- **Human irregularity score** — bare except, print-debugging, magic numbers, naming mix
- File classification (`FileCategory`) — production_logic, dto_mapper, test, generated, vendor, boilerplate_integ, config_infra, migration, example, notebook
- KPI exclusions for vendor and generated files (configurable)
- Mandatory `caveats` and `pct_note` disclaimer on every Origin Estimate
- SARIF 2.1.0 output (`--format sarif`)
- 82 new tests (170 total)

### Changed
- KPI renamed to **AI-Adoption Pattern Index** with explicit "NOT a percentage of AI-generated files" warning
- Vendor path detection extended (vendored, deps, libs, Pods, Carthage, site-packages, dist-packages, etc.)
- Generated path detection extended (openapi, swagger, avro, grpc, proto, kapt-generated, apt-generated, jooq-generated, graphql-generated)
- Git burst detection now filters CVS/SVN/refactor/format/vendor/regenerate commits (15+ keywords)
- All user-facing output uses "pattern signal" language, not authorship language
- Schema bumped to `5.0`; ruleset bumped to `5.0`

### Fixed
- Vendored path false positives (Apache packages, system Python paths)
- Generated path false positives (excluded from KPI denominator)
- Git burst false positives on initial imports and migrations
- Wording in JSON/Markdown outputs that previously implied forensic certainty
- Java DTO and Spring Boot framework code over-flagged as AI-like

### Security
- Anti-misuse guardrails: `developer_fingerprint_enabled = False` by default
- Tool-generated code (protobuf, OpenAPI, jOOQ) explicitly excluded from origin estimates to prevent confusion with LLM-generated

## [4.0.0] — 2026

### Added
- Multi-score model (`ai_likelihood`, `adjusted_score`, `risk_score`, `confidence`, `kpi_score`)
- File classification with KPI weights per category
- Framework detection (Spring, JPA, Lombok, MapStruct, FastAPI, Pydantic, Django)
- 34 language-specific heuristic signals
- Versioned scoring model
- Machine-readable JSON output

### Changed
- Repositioned tool from "AI detector" to "AI-Adoption Pattern Index" KPI
- Improved KPI wording across all outputs

## [3.0.0] and earlier

Initial implementation phases — see git history.
