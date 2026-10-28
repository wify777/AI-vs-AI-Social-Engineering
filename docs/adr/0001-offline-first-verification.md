# ADR-0001: Make archive verification offline and read-only

- Status: Accepted
- Date: 2026-10-28

## Context

The repository combines historical experiment data with scripts that call
third-party model APIs. A reviewer should not need keys, provider availability
or a new paid experiment to inspect the published archive.

## Decision

Add a standard-library verifier with no provider imports. Keep the historical
data unchanged. Check consistency and surface error-bearing records separately.
Use network-disabled tests and a non-root, network-disabled verifier container.

## Alternatives

- Re-run all experiments: requires credentials, time and a corrected protocol;
  it cannot reproduce a fixed historical snapshot exactly.
- Trust the README figures: simple but does not detect archive drift or errors.
- Remove failed records: changes the scientific artifact and may bias estimates.

## Consequences

Reviewers get a fast, reproducible entry point. The verifier establishes only
the facts it checks; it cannot validate treatment assignment or model provenance.
The package wheel contains code, not the full dataset; pass a repository root
to `agenttrust-verify --root /path/to/checkout` after installing a wheel.

## Revisit when

A versioned collection protocol records error classes, intervention configuration,
benign controls and tested recovery alongside each new dataset.
