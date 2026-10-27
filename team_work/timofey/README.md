# Stop diagnostics

A small program that reads a made-up JSON snapshot of a stopped AgentTrust
collection run and explains what to do next. It **only classifies** the
snapshot it is given. It never restarts, retries or touches real processes,
locks, queues or the network, and it does not prove that the snapshot matches
a real machine.

Python 3.12+, standard library only.

## Usage

```
python3 team_work/timofey/diagnose_stop.py team_work/timofey/fixtures/retry_candidate.json
```

Output (JSON on stdout):

```json
{
  "action": "retry_candidate",
  "reason": "network failure with clean proof: no response, decision, confirmation or stub recorded, and budget remains",
  "checks_needed": [
    "check the logs to confirm the failed attempt got no model response and caused no tool action",
    "confirm previous attempts are still saved before any retry",
    "a retry is the operator's decision; this program does not retry"
  ]
}
```

- `action`: one of `running`, `wait_quota`, `review_required`,
  `retry_candidate`, `manual_check`, `finished`, `stop_limit`.
- `reason`: why this action was chosen.
- `checks_needed`: what the operator should check by hand.

Exit code is `0` whenever a result is printed (including `manual_check` for an
invalid snapshot or invalid JSON), and `2` if no file is given or the file
cannot be read.

From Python: `from diagnose_stop import diagnose; diagnose(snapshot_dict)`.
The input dict is never modified.

## Tests

```
python3 -m unittest discover -s team_work/timofey -p 'test_*.py' -v
```

Check `python3 --version` first: on macOS, `python3` may be Apple's 3.9. Use
`python3.12` explicitly if needed.

## Fixtures

Each file in `fixtures/` is the learning input from the task with as few
fields changed as possible. All counts add up.

| Fixture | Changed from the learning input | Expected action |
|---|---|---|
| `retry_candidate.json` | nothing | `retry_candidate` |
| `running.json` | `process_alive`, `lock_busy` true; `running` 1, `failed` 0 | `running` |
| `wait_quota.json` | `quota_wait` true; `http_statuses` `[null, null, 429]` | `wait_quota` |
| `review.json` | `planned` 2, `review` 1 (one job still failed) | `review_required` |
| `integrity.json` | `hashes_match` false | `manual_check` |
| `finished.json` | `completed` 1, `failed` 0, `last_error` null | `finished` |
| `stop_limit.json` | `deadline_expired` true | `stop_limit` |

## Priority table (first match wins)

| # | Condition | Action |
|---|---|---|
| 1 | Missing field, wrong type, negative number or counts that don't add up | `manual_check` |
| 2 | `hashes_match` false, `orphan_stub` true or `evidence_complete` false | `manual_check` |
| 3 | `process_alive` or `lock_busy` true | `running` |
| 4 | `running` > 0 but no live process | `manual_check` |
| 5 | `deadline_expired`, no job attempts left, or `http_reservations_remaining` < `required_http_headroom` (skipped if every job is completed) | `stop_limit` |
| 6 | `quota_wait`, `provider_hold` or any 429 in `http_statuses` (skipped if every job is completed) | `wait_quota` |
| 7 | No running, failed or pending jobs | `finished` |
| 8 | `review` > 0 (and not finished) | `review_required` |
| 9 | Network failure with all proof fields clean (see below) | `retry_candidate` |
| 10 | Anything else | `manual_check` |

In the code, rule 1 is `validate()`, rules 2-9 are the `rule_*` functions
listed in order in `RULES`, and rule 10 is the fallback at the end of
`diagnose()`.

### Validation (rule 1)

- Booleans must be real JSON `true`/`false`. `"false"`, `0` and `null` are rejected.
- Counts and budgets must be whole non-negative numbers. `true`, `1.0` and `"1"` are rejected.
- `last_error` is a string or `null`.
- `http_statuses` is a list whose entries are `null` or a whole number from
  100 to 599. `true`, `"429"`, `429.0`, `99` and `600` are rejected.
- A missing field is never treated as `false`.
- `planned` must equal `completed + review + pending + failed + running`.

### Retry candidate (rule 9)

All of these must hold:

- At least one job has `failed` (`failed >= 1`). Pending-only and
  completed-only snapshots are never retry candidates.
- `last_error` is a network error (`api_error_network`).
- `model_response_received`, `decision_recorded`, `confirmation_recorded` and
  `stub_recorded` are all `false`.
- `previous_attempts_preserved` is `true`.
- `job_attempts_remaining` > 0 and
  `http_reservations_remaining` >= `required_http_headroom`.
- No 429, no `quota_wait`, no `provider_hold`, no live process, no busy lock
  and no integrity problem.

`checks_needed` always tells the operator to check the logs. If any condition
fails, the result is `manual_check` and the reason lists what blocked the retry.

## Design decisions

- **Restrictions beat finished, unless every job is completed.** A run whose
  only unfinished jobs are in review is not allowed to hide an active
  restriction: review-only plus quota/429/hold returns `wait_quota`, and
  review-only plus an expired deadline or spent budget returns `stop_limit`.
  The reason and `checks_needed` then also mention the review jobs.
  Review-only with no restriction is still `finished`, with review listed in
  `checks_needed`.
- **Completed-only with an expired deadline stays `finished`.** When
  `completed == planned` there is nothing left to continue or wait for, so
  rules 5 and 6 are skipped and an expired deadline, spent budget or old 429
  does not change the result.
- **`http_statuses` is assumed to be historical:** every HTTP result of the
  job's attempts so far, oldest first, not only the latest attempt. Because of
  that, any 429 in the list still counts as a quota signal (rule 6) and blocks
  a retry. This is conservative. **Open question for Akhmad:** is the list
  historical or only the current attempt? If it is current-only, a 429 could
  be treated as more urgent and older 429s would not exist in the snapshot.
- **Rule 8 (review_required) is an interpretation.** The task says review jobs
  are not retried and stay in the report when the run is finished, but it does
  not say what to report when review jobs exist next to unfinished ones. We
  chose `review_required`. This is waiting for confirmation from Akhmad. To
  change it, move or remove `rule_review` in the `RULES` list in
  `diagnose_stop.py`.
- **Integrity (rule 2) is checked before a live process (rule 3).** A hash
  mismatch, orphan stub or missing evidence means the data may already be
  wrong, and an operator should know that even while the run is still going.
- **Budget limits come before quota waiting (rule 5 before 6).** Waiting for a
  quota is pointless if the deadline or budget is already gone.
