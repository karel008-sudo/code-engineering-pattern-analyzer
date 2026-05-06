---
name: Feature request
about: Suggest a new heuristic, capability, or improvement
title: '[FEATURE] '
labels: enhancement
---

## Problem this solves

<!-- What scenario is the analyzer currently weak at? -->

## Proposed approach

<!-- Sketch the heuristic, signal, or feature -->

## False-positive considerations

<!-- What legitimate code could trigger this? -->
<!-- This is required — every heuristic has FP modes; we need to think about them upfront -->

## Compatibility with project principles

Confirm the proposal does not:

- [ ] Require external API calls or telemetry
- [ ] Send source code off the user's machine
- [ ] Increase claims of certainty about AI authorship
- [ ] Enable per-developer rankings or surveillance
- [ ] Add heavy runtime dependencies (stdlib + optional `pyyaml` is the budget)

## Alternatives considered

<!-- Other approaches you thought about and why this one wins -->
