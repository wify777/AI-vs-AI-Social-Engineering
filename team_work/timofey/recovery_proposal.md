# Proposal: bounded recovery after a network failure

**Status: proposal only. Nothing here is implemented.** `diagnose_stop.py`
only classifies a snapshot; it never retries.

## Goal

Let an operator safely re-run a job that `diagnose_stop.py` marked
`retry_candidate`, without ever going over the run's attempt budget, HTTP
budget or deadline, and without losing the record of earlier attempts.

## When recovery may start

1. `diagnose()` returns `retry_candidate` for a **fresh** snapshot, taken
   right before the attempt (an old snapshot may no longer be true).
2. The operator has checked the logs, as `checks_needed` asks, and confirms
   that the failed attempt got no model response and caused no tool action.
3. Recovery takes the run lock first. If the lock is busy or a process is
   alive, it stops (same as rule 3).

## Bounded retries

- Each job may be retried at most `job_attempts_remaining` times. The run as a
  whole also has a cap, for example 3 recoveries per operator session, so one
  bad network day cannot burn through every job's attempts.
- The attempt counter goes down **before** the request is sent and is saved
  immediately. If recovery crashes mid-attempt, that attempt is still counted.
- Only jobs in `failed` with a network error are retried. `review` jobs are
  never retried. `completed` jobs are never touched.

## Pause between attempts

- Wait between attempts with a growing pause, for example 30 s, 60 s, 120 s,
  capped at 10 minutes, plus a small random extra delay so jobs don't retry at
  the same moment.
- A 429, `quota_wait` or `provider_hold` ends recovery and hands over to
  `wait_quota`. Recovery does not try to outwait a quota by itself.
- A pause must never run past the deadline. If the next attempt would start
  after the deadline, recovery stops with `stop_limit`.

## Preserving budget and deadline

- Before each attempt, `required_http_headroom` HTTP requests are reserved.
  If `http_reservations_remaining` is below that, recovery stops
  (`stop_limit`). Unused reservations are returned after the attempt.
- Recovery never resets or raises `job_attempts_remaining`,
  `http_reservations_remaining` or the deadline. They carry over unchanged
  from the original run.
- Every attempt is **added** to the job's history, never written over it, so
  `previous_attempts_preserved` stays true.

## After each attempt

Run `diagnose()` again on the new snapshot:

| New result | Recovery does |
|---|---|
| `finished` | stop, success |
| `retry_candidate` | pause, then try again if attempts remain |
| anything else | stop and report the action and reason to the operator |

If any proof field becomes true (a response, decision, confirmation or stub
was recorded), the job is no longer safe to retry. The next diagnosis will
return `manual_check`, and recovery stops.

## Audit record per attempt

Job id, attempt number, start/end time, pause before it, HTTP statuses,
`last_error`, budget before/after, and the diagnosis before and after.

## Open questions

- Pause values and the per-session cap: who decides them?
- Should a 429 during recovery use up a job attempt?
- Does each attempt need operator approval, or only the first?
