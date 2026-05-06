## Summary

<!-- One paragraph: what changes and why -->

## Type of change

- [ ] Bug fix
- [ ] New heuristic / signal
- [ ] False-positive reduction
- [ ] Language coverage extension
- [ ] Reporting / UX improvement
- [ ] Documentation
- [ ] Refactor (no behavior change)

## Verification

- [ ] All existing tests pass (`for f in tests/test_*.py; do python3 "$f"; done`)
- [ ] New tests added for new behavior
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] If new heuristic: rationale + FP cases documented in `_signal_metadata.py`
- [ ] If user-facing output changed: language reviewed against the no-forensic-certainty rule

## False-positive review

<!-- For new heuristics: list legitimate code that might trigger this and how the test suite covers it -->

## Notes for reviewer

<!-- Anything specific you want feedback on -->
