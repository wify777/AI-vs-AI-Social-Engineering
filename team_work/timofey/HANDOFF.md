# HANDOFF: stop diagnostics (Closes #8)

## What was done

- `diagnose_stop.py`: `diagnose(snapshot)` returns `action`, `reason` and
  `checks_needed`; CLI `python3 diagnose_stop.py snapshot.json`. Python 3.12+,
  standard library only. No HTTP, subprocess, real processes, locks or queues.
- `fixtures/`: 7 snapshots (retry_candidate, running, wait_quota, review,
  integrity, finished, stop_limit), each the learning input from the task
  with only the needed fields changed. All counts add up.
- `test_diagnose_stop.py`: 30 tests covering all 7 fixtures, priority
  combinations, strict type checks, count consistency, unchanged input and
  the CLI.
- `README.md`: usage, priority table, validation rules, design decisions.
- `recovery_proposal.md`: one-page proposal for bounded recovery. Not
  implemented.

## How to verify

From the repository root:

```
python3 -m unittest discover -s team_work/timofey -p 'test_*.py' -v
python3 team_work/timofey/diagnose_stop.py team_work/timofey/fixtures/retry_candidate.json
```

Check `python3 --version` first. On macOS `python3` may be Apple's 3.9; use
`python3.12` if so.

## Actual results (2026-10-22)

```
Python 3.12.13
Ran 30 tests in 0.002s
OK
```

The same 30 tests also pass on Python 3.9.6. The CLI on
`retry_candidate.json` returns `retry_candidate` with "check the logs..." in
`checks_needed`.

Each fixture gives its expected action:

| Fixture | Action |
|---|---|
| retry_candidate | retry_candidate |
| running | running |
| wait_quota | wait_quota |
| review | review_required |
| integrity | manual_check |
| finished | finished |
| stop_limit | stop_limit |

## Where AI helped

I used Claude Code. I gave it the task file, the priority order of the rules
and the list of test combinations. It wrote the fixtures, code, tests and
first drafts of the documents, one step at a time, and explained each part.
I reviewed each step before moving on. The design choices (rule order,
strict types, finished beating stop_limit) are mine.

## Time spent

About 2-3 hours

## Open questions

1. **Review rule (rule 8).** When review jobs exist next to failed or pending
   jobs, I return `review_required`. The task text doesn't say this directly.
   Akhmad, is this right? It is one line in `RULES` to change.
2. **Finished vs stop_limit.** A run where every job is terminal is `finished`
   even if the deadline has expired. Is that the intended reading?
3. **Retry with no failed job.** Resolved in the Stage 1 fix: retry now
   requires `failed >= 1`.
5. **`http_statuses`: historical or current?** Assumed historical (all
   attempts so far), so any 429 in the list blocks a retry. See README.
4. **Network error names.** Only `api_error_network` counts as a network
   error. Are there other `last_error` values that should count?
