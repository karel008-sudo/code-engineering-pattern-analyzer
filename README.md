# AI Code Pattern Analyzer

A heuristic analysis tool that estimates **AI-like code characteristics** in Git repositories.
It operates entirely offline using structural and stylistic code signals — no ML models, no external APIs, no LLM calls, no embeddings.

> **Important framing:** This tool does not detect AI-generated code with certainty.
> It measures the presence of heuristic signals that are statistically correlated with generated, templated, or mechanically produced code.
> Results are directional indicators, not forensic proof of AI origin.

---

## Contents

- [What this tool does](#what-this-tool-does)
- [Quick start](#quick-start)
- [Methodology](#methodology)
- [Heuristic signals](#heuristic-signals)
- [Scoring interpretation](#scoring-interpretation)
- [KPI usage](#kpi-usage)
- [Limitations](#limitations)
- [Recommended and non-recommended usage](#recommended-and-non-recommended-usage)
- [Supported languages](#supported-languages)
- [Output formats](#output-formats)
- [Requirements](#requirements)

---

## What this tool does

The analyzer scans source code repositories and produces a per-file and per-repository **AI-likeness score** — an estimate of how much the code exhibits stylistic and structural characteristics often associated with AI-assisted or mechanically generated code.

It is best understood as a **directional proxy for AI-assisted development adoption**, useful for:

- repository-level trend monitoring
- team-level adoption signals
- comparing repositories or branches over time
- identifying files that warrant manual review

It is **not** a forensic classifier, a compliance tool, or a reliable measure of individual developer contribution.

---

## Quick start

```bash
# Scan one or more repositories
python -m ai_pattern_analyzer --dirs ./my-repo

# Full analysis with AST, entropy, git metadata, and cross-file similarity
python -m ai_pattern_analyzer \
  --dirs ./repo1 ./repo2 \
  --ast --entropy --include-git --similarity

# Output as JSON (suitable for dashboards and pipelines)
python -m ai_pattern_analyzer --dirs ./repo --output json > report.json

# Output as CSV (suitable for spreadsheet analysis)
python -m ai_pattern_analyzer --dirs ./repo --output csv > data.csv

# Exclude test files, use 4 parallel workers
python -m ai_pattern_analyzer --dirs ./repo --exclude-tests --workers 4
```

### All CLI flags

| Flag | Description |
|---|---|
| `--dirs DIR [DIR ...]` | Directories (repositories) to scan. Required. |
| `--output table\|json\|csv` | Output format. Default: `table`. |
| `--ast` | Enable Python AST-based structural analysis. |
| `--entropy` | Enable lexical entropy and type-token ratio analysis. |
| `--similarity` | Compute cross-file TF-IDF cosine similarity (O(n²), slower on large repos). |
| `--include-git` | Analyze git commit history for burst patterns and author diversity. |
| `--include-tests` | Include test files in analysis (tracked separately by default). |
| `--exclude-tests` | Exclude test files entirely. |
| `--workers N` | Number of parallel worker processes. Default: `cpu_count − 1`. |
| `--no-color` | Disable ANSI color in table output. |
| `--quiet` | Suppress per-file progress output. |

---

## Methodology

The analyzer measures **stylistic and structural code signals** at the file level. These signals are aggregated using language-specific weighted scoring into a per-file `ai_likelihood` value between 0.0 and 1.0.

### What the score measures

The score captures the degree to which a file's structure, naming conventions, documentation patterns, exception handling style, and lexical characteristics **resemble patterns that are statistically more common in AI-assisted or mechanically produced code** compared to hand-written code in the same language.

### What can influence the score

High AI-likeness scores are not exclusive to AI-generated code. The same patterns may appear naturally in code produced by:

- senior developers with clean, consistent coding habits
- teams following strict linting and formatting standards
- IDE auto-formatters (Black, google-java-format, Prettier)
- framework-driven boilerplate (Spring, JPA, OpenAPI clients)
- generated DTOs, mappers, API clients, schema classes
- enterprise CRUD patterns and repetitive domain logic
- heavily refactored or uniformly templated legacy codebases
- Copilot-style incremental suggestion acceptance

Results must always be interpreted **in context**, not in isolation.

### Analysis layers

| Layer | Description | Flag |
|---|---|---|
| Heuristic signals | 12 language-specific code-style signals | always on |
| Lexical entropy | Token distribution and repetition patterns | `--entropy` |
| AST analysis | Python abstract syntax tree: depth, node diversity, function length | `--ast` |
| Cross-file similarity | TF-IDF cosine similarity between files in same repository | `--similarity` |
| Git metadata | Commit burst detection, author diversity, message style | `--include-git` |

---

## Heuristic signals

Signals are classified by their empirical discriminating power based on calibration against repositories with known human/AI composition ratios.

### Stronger supporting signals

These signals show higher separation between AI-like and human-like code in calibration data. They carry higher weight in the scoring model.

| Signal | Description |
|---|---|
| **Exception handling quality** | Specific exception types with reraise or `from`-chaining correlate with AI patterns. Bare `except:` or swallowed exceptions are strong human indicators. |
| **Empty catch blocks** | `catch (Exception e) {}` and `e.printStackTrace()` are near-exclusive human signals in production Java code. |
| **Function length and decomposition** | AI tends toward shorter, focused functions. Human code more frequently contains long, multi-purpose methods. |
| **Token repetition / lexical entropy** | Low lexical diversity (high repetition ratio) correlates with generated, templated, or mechanically expanded code. See dedicated section below. |
| **Stream API vs. loop usage** (Java) | Heavy use of Stream API with method chaining is more common in AI-generated Java. Index-based loops are a human signal. |
| **Boilerplate-like structural regularity** | Uniform file structure, consistent naming schemes, and symmetric method organization are more common in generated code. |

### Weaker or highly contextual signals

These signals are valid supporting evidence but are easily confounded by team standards, tooling, and project type. They carry lower weight and should not be interpreted independently.

| Signal | Description | Common confounders |
|---|---|---|
| **Comment density** | AI tends to over-comment; high comment ratio is a weak AI signal. | Documentation standards, Javadoc requirements, legacy code |
| **Docstring quality** | Structured `Args:`/`Returns:` blocks correlate with AI. | Team documentation standards, Sphinx requirements |
| **Variable naming** | AI avoids abbreviations; human code uses `res`, `tmp`, `ctx`. | Senior developer habits, team conventions |
| **Type annotation density** (Python) | AI annotates comprehensively; humans often annotate selectively. | Mypy/Pyright enforcement, modern Python standards |
| **Line length consistency** | AI produces more uniform line lengths; human code shows higher variance. | Formatters, linters |
| **Logging quality** | Parameterized SLF4J/loguru calls are an AI signal; string concatenation in logs is human. | Team logging standards |

### Token repetition / lexical entropy

**Purpose:** Detects unusually repetitive token patterns that may indicate generated, templated, or mechanically expanded code.

**How it works:**

```python
def h_token_repetition(text):
    tokens = re.findall(r"\w+", text.lower())
    if len(tokens) < 50:
        return 30  # insufficient data

    freq = Counter(tokens)
    repetition_ratio = sum(v for v in freq.values() if v > 3) / len(tokens)

    if repetition_ratio > 0.6: return 75
    if repetition_ratio > 0.4: return 55
    if repetition_ratio > 0.25: return 35
    return 15
```

The `repetition_ratio` measures what fraction of all tokens are drawn from a small set of frequently repeated terms (appearing more than 3 times). AI-generated or mechanically generated code tends to reuse structural phrases, helper terminology, naming patterns, and semantically similar constructs more densely than typical hand-written code.

**Interpretation:** This is a **supporting signal, not a decisive classifier**. High token repetition appears naturally in:

- DTO classes and data mappers
- generated API clients and schema classes
- enterprise CRUD layers with standard field patterns
- test fixtures with repeated assertion patterns
- files following strict naming conventions

High repetition alone is not sufficient to conclude AI involvement. It should be interpreted alongside other signals.

**Complementary signal — lexical entropy (`--entropy` flag):**

Shannon entropy of the token distribution provides a normalized view of vocabulary richness. Low normalized entropy indicates that the file draws from a narrow vocabulary repeatedly — a pattern consistent with mechanically generated code. High entropy indicates lexical variety, which is more common in hand-written logic.

---

## Scoring interpretation

Scores are expressed as `ai_likelihood` in the range 0.0–1.0, derived from a non-linear weighted aggregation of active signals, passed through a sigmoid normalization.

| Range | Interpretation |
|---|---|
| **0.00–0.25** | Low presence of AI-like or automation-like signals. Code characteristics are consistent with typical hand-written code for this language. |
| **0.26–0.50** | Moderate presence of AI-like signals. May be fully explained by coding style, framework conventions, formatting tools, or standard enterprise patterns. |
| **0.51–0.75** | Elevated AI-like signal density. Warrants review alongside repository context: team conventions, tooling, code generation pipelines, and development history. |
| **0.76–1.00** | High concentration of AI-like or mechanically generated characteristics. Strong candidate for further review. Does not constitute proof of AI origin. |

### Additional output fields

| Field | Description |
|---|---|
| `confidence` | Fraction of weighted signal mass that agrees with the score direction. Low confidence indicates mixed or contradictory signals. |
| `classification` | `AI-like` / `human-like` / `mixed` / `uncertain` — based on likelihood and confidence thresholds combined. |
| `top_signals` | The four signals contributing most to the score for this file. Use for explainability. |

Scores are calibrated per repository using percentile statistics (`p25`, `p75`, `p90`). File scores are best interpreted relative to the repository's own distribution, not against a universal absolute threshold.

---

## KPI usage

The tool output can be used as an engineering KPI under the following framing:

**Suitable KPI forms:**
- *AI-assisted development adoption proxy* — estimated share of repository code with elevated AI-like characteristics
- *AI-like code production indicator* — trend metric across sprints or quarters
- *Repository-level heuristic signal* — directional, comparative, time-series

**How to interpret this KPI correctly:**

- **Directionally:** Is the share increasing or decreasing over time?
- **Comparatively:** How does one repository or team compare to another, controlling for language and code type?
- **At aggregate level:** Repository or team level, not individual file or individual developer level.
- **In combination:** Alongside developer surveys, IDE telemetry, pull request metadata, commit-level analysis, and engineering productivity metrics.

**This KPI is not suitable for:**
- evaluating individual developer performance
- making contractual or compliance claims about AI-generated code contribution
- measuring exact AI contribution percentages
- security or legal classification of code origin

Scores should never be presented as ground truth. They are trend indicators with known false positive and false negative rates.

---

## Limitations

### False positives (high score, not AI-generated)

The tool may produce elevated scores for code that is not AI-generated:

- **Senior developer code:** Clean, consistent, well-structured code from experienced engineers may score higher than messier junior code.
- **Strict formatting and linting:** Teams using Black, Prettier, google-java-format, or similar tools produce uniformly structured code that resembles AI output.
- **Generated boilerplate:** DTOs, API clients, OpenAPI-generated classes, JPA entities, protocol buffer outputs, and schema mappers naturally exhibit high structural regularity.
- **Enterprise CRUD patterns:** Standard layered architectures with service/controller/repository patterns produce repetitive, regular code.
- **Heavy refactoring:** A large uniform cleanup or extraction refactor produces code that looks structurally consistent.
- **Framework conventions:** Spring Boot, Quarkus, Django, and similar frameworks enforce patterns that resemble AI-generated structure.

### False negatives (low score, actually AI-generated)

The tool may miss AI-generated code when:

- **A developer significantly edited AI output** before committing.
- **Copilot suggestions were accepted incrementally** across many small commits, mixing naturally with human edits.
- **AI-generated code is intentionally irregular** or was prompted to match an existing style.
- **Junior developer code lacks clean structure**, making AI code indistinguishable by style alone.
- **The same file mixes significant human and AI contributions** — the score reflects the aggregate, not individual sections.
- **Terse AI-generated code** (short utility functions, simple lambdas) exhibits fewer AI-like patterns.

---

## Recommended and non-recommended usage

### Recommended

- Repository-level trend monitoring over time
- Team-level AI adoption proxy metric
- Comparing AI-like signal density across repositories or branches
- Identifying files that are candidates for manual review
- Supporting broader AI adoption measurement programs alongside other signals
- Engineering leadership dashboards as one of multiple indicators

### Not recommended

- Judging or evaluating individual developers based on scores
- Making contractual or compliance claims about AI-generated code percentages
- Exact measurement of AI contribution in code reviews
- Security or legal classification of code origin
- Replacing engineering code review with automated verdicts
- Performance evaluation of developers without additional context and qualification

---

## Supported languages

| Language | Heuristic signals | AST analysis | Notes |
|---|---|---|---|
| Python | Full (11 signals) | Full (stdlib `ast`) | Strongest support |
| Java | Full (12 signals) | Regex-based approximation | Strongest Java signal: Stream API, empty catch |
| Kotlin | Java signal set | Regex-based | |
| TypeScript | Partial (11 signals) | — | |
| JavaScript | Partial (11 signals) | — | |
| Vue | TypeScript signal set | — | |
| Go, Rust, C#, Ruby, PHP, Swift | Partial (7 signals) | — | Language-specific weights not calibrated |
| CSS, SCSS, SQL | Minimal signals | — | Structural patterns only |

---

## Output formats

### Table (default)

Terminal output with per-repository summary, score distribution histogram, top AI-like and most human-like files, and git signal breakdown.

### JSON (`--output json`)

Structured output including full signal breakdown per file, repository statistics (mean, median, standard deviation, percentiles), classification counts, and git signals. Includes schema version and disclaimer text.

```json
{
  "schema_version": "3.0",
  "disclaimer": "...",
  "repos": [{
    "repo": "my-repo",
    "summary": {
      "median_likelihood": 0.231,
      "p75": 0.381,
      "ai_like_pct": 3.2
    },
    "files": [{
      "file": "src/Service.java",
      "language": "Java",
      "ai_likelihood": 0.547,
      "confidence": 0.61,
      "classification": "mixed",
      "top_signals": { "stream_usage": 0.21, "log_quality": 0.09 }
    }]
  }]
}
```

### CSV (`--output csv`)

One row per file with columns: `repo`, `file`, `language`, `kind`, `lines`, `ai_likelihood`, `confidence`, `classification`. Suitable for spreadsheet analysis and pipeline integration.

---

## Architecture

```
ai_pattern_analyzer/
├── config.py              — language definitions, signal keys, per-language weights
├── scanners/
│   ├── filesystem.py      — file discovery, generated/test/vendor classification
│   └── git.py             — git commit history extraction
├── analyzers/
│   ├── lexical.py         — Shannon entropy, type-token ratio, repetition index
│   ├── structural.py      — Python AST analysis, Java structural approximation
│   ├── heuristics.py      — 12 language-specific code-style heuristics
│   ├── similarity.py      — TF-IDF cross-file cosine similarity
│   ├── git_signals.py     — commit burst, author diversity, message entropy
│   └── pipeline.py        — multiprocessing-safe worker entry point
├── scoring/
│   ├── model.py           — non-linear aggregation, sigmoid normalization, confidence
│   └── calibration.py     — per-repository percentile statistics and tier assignment
└── reporting/
    ├── cli.py             — terminal output with histograms and color
    └── json_report.py     — structured JSON with schema versioning and disclaimer
```

---

## Requirements

- Python 3.8+
- Standard library only (no pip dependencies for core functionality)
- `git` CLI available in `PATH` for `--include-git` flag
- Optional: `multiprocessing` support (available on all platforms; Pool disabled on <20 files)

---

## Disclaimer

This tool detects **code generation patterns** using statistical heuristics. It does not identify authorship, prove AI usage, or constitute evidence for any contractual, compliance, legal, or personnel claim. Results are probabilistic pattern signals and should be interpreted as directional trend indicators only.

High AI-likeness scores reflect stylistic and structural code characteristics — they are not a reliable measure of whether any specific code was generated by an AI system.
