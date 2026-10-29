# Explicit format mapping

The original utility uses `{ "annotations": [...] }` and stores a `category`, `explanation`, `timestamp`, `source_hash`, and `context`. The preserved reference uses a **JSON array**. This bridge intentionally does **not** perform an automatic conversion: a context-only export cannot establish the original case ID or source-record identity.

| Original tool | Preserved form | Rule |
|---|---|---|
| `category` | `secondary_category` | Only one of the five fixed policy categories |
| `explanation` | `evidence_note` | Preserve exact text |
| `timestamp` | `annotated_at` | Require ISO-8601 with timezone |
| `annotator_identity` | `annotator_identity` | Preserve exact text |
| `source_hash` | `source_record_sha256_excluding_newline` | Only if independently proven to refer to exact original JSONL line bytes |
| `config_hash`, `run_id`, `stage` | same named fields | Exact match required |
| `context` | none | No automatic transfer; original evidence stays separate |
| no reliable `case_id` | `case_id` | Must come from trusted identity manifest; never invent |
| old policy marker | `policy_version`, `policy_sha256` | Must match provided identity manifest; never guess |

Original source-record SHA-256 is calculated on the **exact original JSONL record bytes excluding only a terminal LF or CRLF**. It is not a hash of Markdown, a parsed JSON object, or a reserialized export. The bridge copies this value unchanged from ANNOTATIONS.json. `manifest.json` separately stores SHA-256 of the exact bytes of EVIDENCE.md, ANNOTATIONS.json and each generated reviewer form. The latter are packaging/provenance hashes, never substitutes for source-record hashes.

No adapter is included because there is no trusted mapping from every legacy `context` to all 58 preserved identities. This avoids silently conflating distinct runs.
