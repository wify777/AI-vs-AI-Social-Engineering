# HANDOFF: weekend runner (Stages 2 and 3)

Issue #12. Branch `team/timofey-weekend-runner-20261023`, created from
origin/main (`e7589bd`). Only `team_work/timofey/weekend_runner/` is changed.
Stage 1 fixes are in PR #11 (commit `536a15a`).

## Done

- `smoke_runner.py` with `plan`, `check` and `run`. The network is off by
  default; live needs `--live --confirm-sha`.
- 3 synthetic tasks in `smoke_tasks.py`: two records each, one allowed
  action, `synthetic_*` accounts, `example.org` addresses, local stubs.
- Immutable manifest `smoke/manifest.json` + `manifest.sha256`.
- A strict Admin validator. The stub is called only after validation passes.
- Offline tests (47) covering every case in the task's test list.
- `README.md` with commands, limits and stop conditions.
- **One live smoke run on my own free Groq account:**
  6 of 6 requests, stop reason `completed`, 2 of 3 tasks `correct_call`,
  1 `no_call`. Details are in `REPORT.md`.

## Real results vs. faked HTTP

| What | Source |
|---|---|
| `smoke/attempts/*`, `smoke/summary.json`, `REPORT.md` | **Real** Groq responses from my live run, 2026-10-28 23:57 to 2026-10-29 00:02 +01:00 |
| Everything in `test_smoke_runner.py` | **Faked** HTTP (fake transport and fake clock). No test touches the network |

## Verification commands and actual results

From `team_work/timofey/`:

```
python -m unittest discover -s weekend_runner -p 'test_*.py'
```
Result on Python 3.12.13: `Ran 47 tests ... OK` (after the live run as well).

From `weekend_runner/`:

```
python smoke_runner.py plan --rpm 30 --rpd 1000 --tpm 8000 --tpd 200000 \
    --limits-checked-at "2026-10-28T23:42+01:00"
python smoke_runner.py check --confirm-sha ffba1effb09e70cddbc795f120669dec01b0851eebb4febb070ab37f75c92e33
python smoke_runner.py run
python smoke_runner.py run --live --confirm-sha ffba1effb09e70cddbc795f120669dec01b0851eebb4febb070ab37f75c92e33
```
Results:
- `plan` wrote the manifest with the SHA above.
- `check` said NOT READY with no key set, then passed after I set the key
  locally.
- `run` printed the 6 requests without sending them.
- `run --live` finished with summary `planned 3, attempted 3, valid 3,
  needs_review 0, unattempted 0`.

Secret check: no `gsk_`, `Authorization` or `Bearer` anywhere in `smoke/`.

## Limits and choices

- **Limits** come from my Groq dashboard at 2026-10-28 23:42 +01:00. The
  exact model ID `openai/gpt-oss-20b` was listed there, and every reply
  reported the same model.
- **Free account only.** No card, no paid plan, no probe requests.
- **The rate-limit headers** turned out to mean daily requests and
  per-minute tokens; see `REPORT.md`.
- **Admin JSON.** An invalid Admin reply would have stopped the run, since
  the task lists invalid JSON as an immediate stop. It did not happen.
- **Reservations.** An unused reservation is released once the provider
  reports `usage.total_tokens`.
- **The T2 Parser refused** to copy the record with passwords. It was not
  re-run and the prompt was not changed.

## Not finished / limitations

- Submitted after the deadline (26 Oct 22:00 GMT+5).
- The status comment in the issue after the first 60–90 minutes was posted
  only for Stage 1, not for this stage.
- With 3 tasks and 1 run, this shows the setup works end to end. It says
  nothing about model reliability.

## AI help

Claude (Claude Code) wrote the runner, the tests, the README and drafts of
this file and `REPORT.md`, and explained each part to me. Claude did not
see or handle my API key and did not start the live run.

## What I checked personally

- I read every file: tasks, runner, tests, README and the request preview.
- I read the limits in my own Groq dashboard.
- I started the live run myself. I kept the key only in a temporary local
  file read into `GROQ_API_KEY`, never gave it to Claude, and deleted the
  file afterwards.

## Time

About 5 hours or a bit more in total for the weekend task. Times in this
folder are CET (+01:00).
