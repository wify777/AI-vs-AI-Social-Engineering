# Working on AgentTrust

Start with `python -m evaluation.verify_dataset` from the repository root.
It reads the archived data; it does not contact an LLM provider.

## Local checks

Python 3.12 is the reference development environment.

```bash
python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check evaluation/verify_dataset.py tests
python -m pytest --cov --cov-report=term-missing
python -m evaluation.verify_dataset
python -m build
```

Pytest only collects `tests/` and disables network sockets. Root-level
`test_*.py` files are legacy live-provider diagnostics, not unit tests.
Do not add API credentials to CI or disable the network guard to make a test pass.

Ruff currently checks critical errors across the codebase. Formatting is enforced
on the verifier and new tests; the legacy research scripts have not been
mass-reformatted. Coverage includes the source packages, including untested code.
There is no claim of complete provider-adapter or end-to-end coverage.

## Changes

Use short-lived branches (`fix/log-path`, `docs/methodology`, `test/provider-errors`)
and small pull requests into `main`. Explain the problem, the change, the checks
run and any remaining risks. Do not rewrite published history for a tidier graph.

Commit examples:

```text
fix(logging): support a log filename without a parent directory
test(archive): detect duplicate experiment identities
docs(methodology): distinguish provider failures from refusals
```

## Research data

- Preserve the published v3 log and statistics. New collections belong in a
  versioned dataset, not appended to the historical snapshot.
- Report provider errors, refusals and completed tool calls separately.
- Record the code revision, model identifier, provider, prompts and actual
  intervention configuration for new runs.
- Review `docs/reproducibility-audit.md` before interpreting old comparisons.
- Use only fictional data and the existing stub tools. No real administrative
  services are needed for this benchmark.
- Keep keys in local environment variables. Revoke exposed credentials before
  attempting repository cleanup; removing a file does not remove Git history.

## Licensing

The repository does not yet declare a license. Do not assume permission to
redistribute it. The contributors need to agree on code and dataset licenses
before one is added.
