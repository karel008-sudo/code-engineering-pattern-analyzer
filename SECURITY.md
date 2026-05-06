# Security Policy

## Threat model

This analyzer reads source code as text. It:

- **Does not execute** any analyzed code
- **Does not import** modules from the analyzed repository
- **Does not transmit** source code anywhere — no API calls, no telemetry, no external dependencies for core analysis
- **Does not extract** secrets, credentials, or PII
- **Does not require** network access (air-gapped compatible)

The intended deployment is **local execution** on a developer machine, in CI runners, or in containerized scanning jobs.

## Reporting a vulnerability

If you discover a security issue, please **do not open a public issue**.

Instead, report privately via GitHub Security Advisories:
**[https://github.com/karel008-sudo/code-engineering-pattern-analyzer/security/advisories/new](https://github.com/karel008-sudo/code-engineering-pattern-analyzer/security/advisories/new)**

I will acknowledge within **5 working days** and aim to triage within **10 working days**. Coordinated disclosure timelines are preferred.

## Scope

In scope:
- Path traversal or directory escape during scanning
- Accidental code execution from analyzed sources
- Secret leakage in output (logs, JSON, SARIF, Markdown reports)
- Bypass of privacy controls (`privacy_mode`, `developer_fingerprint_enabled`)
- Denial of service via crafted input (e.g. pathological regex inputs causing ReDoS)

Out of scope:
- False positives or false negatives in heuristic scoring (these are documented limitations, not bugs)
- Inability to detect AI-generated code with certainty (this is by design — see README §Disclaimer)

## Anti-misuse considerations

This tool has explicit anti-misuse guardrails (see README §Ethics and anti-misuse). Reports of misuse **scenarios** that bypass those guardrails (e.g. configurations that produce per-developer rankings) are also welcome.
