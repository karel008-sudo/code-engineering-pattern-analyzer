# Contributing to Code Engineering Pattern Analyzer

Thanks for your interest. This project values **defensible heuristics over speculation** and **privacy by default**. Contributions that strengthen those values are very welcome.

## What kinds of contributions are useful

- **New heuristic signals** — with a documented rationale, expected false-positive cases, and tests
- **False-positive reductions** — cases where the analyzer overclaims AI origin on legitimate code
- **Language coverage** — extending to Go, Rust, C#, Ruby, PHP from minimal to full
- **Reporting improvements** — clearer language, more actionable outputs, better UX
- **Documentation** — clarifying methodology, ethics, or limitations
- **Bug fixes** — anything that doesn't match documented behavior

## What I am unlikely to merge

- Changes that increase claims of certainty (the tool produces *pattern signals*, not authorship proof — this framing is non-negotiable)
- Features that require external API calls, telemetry, or sending source code off the machine
- Removing the anti-misuse guardrails (developer fingerprint stays disabled by default; per-developer rankings stay forbidden)
- Adding heavy dependencies — the core must remain Python stdlib only

## Development setup

```bash
git clone https://github.com/karel008-sudo/code-engineering-pattern-analyzer.git
cd code-engineering-pattern-analyzer
python3 -m ai_pattern_analyzer --dirs ./ai_pattern_analyzer --profile quick
```

Optional dev dependency: `pyyaml` for richer config parsing (a fallback parser is built in).

## Running tests

```bash
for f in tests/test_*.py; do python3 "$f"; done
```

170 tests should pass. New heuristics must include tests.

## Pull request expectations

- Single concern per PR
- Tests for new signals or behavior changes
- Update `CHANGELOG.md` under the `## [Unreleased]` section
- For new heuristics: a short note in `_signal_metadata.py` explaining what the signal measures and known false-positive cases
- For wording changes in user-facing output: ensure no language implies forensic certainty (e.g. avoid "this code was AI-generated"; prefer "AI-like pattern signals detected")

## Reporting issues

See [SECURITY.md](SECURITY.md) for security-sensitive reports.
For everything else, open an issue using the provided templates.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
