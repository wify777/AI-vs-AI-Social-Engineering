# Reproducibility audit — published v3 archive

Reviewed on 2026-10-28. This note separates verifiable archive facts from
scientific conclusions that the current checkout cannot establish.

## What can be reproduced offline

Run from the repository root, without installing dependencies or setting API keys:

```bash
python3 -m evaluation.verify_dataset
```

The verifier checks JSONL structure, unique model/payload/condition/repetition
identities, payload/category membership and the published overall, model,
category and condition counts and arithmetic percentages. It emits SHA-256
hashes of the input artifacts. It does **not** verify confidence intervals,
p-values, provider identities, experimental provenance or causal conclusions.

The checked-in output is `results/dataset_audit_v3.json`.

## Confirmed archive facts

- 2,475 records with unique experiment identities.
- 60 distinct payload IDs and six recorded model labels.
- 170 records marked `outcome.tool_executed = true`.
- 1,931 records contain `[ERROR:` in at least one agent response.
- 25 of the 170 recorded tool executions also have an error marker in an agent response.

| Recorded model label | Records | Records with an error marker | Recorded tool executions |
|---|---:|---:|---:|
| openai/gpt-oss-120b | 540 | 318 | 36 |
| openai/gpt-oss-20b | 540 | 323 | 72 |
| minimax/minimax-m3:free | 540 | 540 | 0 |
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 540 | 467 | 60 |
| gemini-flash-latest | 146 | 141 | 0 |
| gemini-3.6-flash | 169 | 142 | 2 |

These are exact text-marker counts, not a complete adjudication of valid and
invalid trials. A response without this marker is not automatically valid.
The original records and aggregate statistics have not been changed.

## Why historical ASR is not a validated ranking

The legacy statistics include error-bearing records in their denominator.
Provider unavailability or request failure is not evidence that a model resisted
an attack. In particular, zero tool calls from a label with error markers in
every record cannot be presented as evidence of strong resistance.

No replacement ranking is calculated here. Simply dropping marked records could
introduce selection bias; a new protocol needs explicit error classification,
retry rules, denominator definitions and benign controls.

## Condition labels are not intervention provenance

In the current source, `ExperimentRunner.run_single_attack` passes `condition`
to `MessageBus.orchestrate_attack`. That method records the label but does not
branch on it to change the Admin input or implement a confirmation mechanism.

A separate `run_conversation(..., source_text=...)` helper can include labeled
source text, but the primary runner does not call that helper. Its existence
does not prove that the archived `with_source_text` records received a treatment.

Consequently, the current checkout does not reproduce a defense comparison
merely by running three condition names. Historical labels alone cannot establish
that different interventions were applied. Do not describe the old condition
comparison as proof that either defense works or fails.

## Other boundaries

- Eight benign seed records exist under `payloads/benign/`; the published v3
  attack log does not establish a completed benign-control evaluation or FPR.
- The Admin path uses model-generated text and flexible JSON parsing, not a
  provider-native function-calling protocol or a hard authorization boundary.
- The tools are local stubs. `tool_executed` records a stub invocation, not
  deletion, email delivery, password modification or SQL execution on a real system.
- The primary runner appends to a log and reuses checkpoint paths. Run new
  collections only after adding explicit dataset isolation and tested recovery.
- Old paper drafts and figures remain available as historical artifacts, not
  independently validated publication-ready findings.

## Next protocol

Before collecting a new dataset:

1. Implement and test each intervention at the actual call site.
2. Separate API errors, parsing errors, refusals, attempted calls and stub execution.
3. Add benign controls and a defined false-positive metric.
4. Write new results to a separate versioned directory.
5. Save the code revision, prompts, provider response metadata and configuration.
6. Test interruption recovery without skipping or duplicating jobs.
7. Recompute statistics under a documented analysis plan.

## What passing CI means

CI checks offline regression tests, critical-error lint, archive consistency,
Python package builds and the isolated verifier container. It does not call
live models and does not certify the scientific conclusions of the legacy draft.

`python3 -m evaluation.verify_dataset --require-clean` intentionally exits
nonzero for this snapshot because error-bearing records are present.
