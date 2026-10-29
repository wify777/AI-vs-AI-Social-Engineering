# Independent review bridge

Python 3.12+, standard library only. All tools are offline. Do not commit the supplied reference materials or filled reviewer forms. Commands run from repository root.

```bash
python3 team_work/indira/weekend_review_bridge/review_bridge.py prepare --identities /path/to/ANNOTATIONS.json --evidence /path/to/EVIDENCE.md --output /tmp/indira_review_forms
python3 team_work/indira/weekend_review_bridge/review_bridge.py validate --reference /path/to/ANNOTATIONS.json --form /tmp/indira_review_forms/reviewer_A.json
python3 team_work/indira/weekend_review_bridge/review_bridge.py validate --reference /path/to/ANNOTATIONS.json --form /tmp/indira_review_forms/reviewer_B.json
python3 -m unittest discover -s team_work/indira/weekend_review_bridge -p 'test_*.py' -v
```

After **two independently completed human reviews**, use:

```bash
python3 team_work/indira/weekend_review_bridge/review_bridge.py compare --reference /path/to/ANNOTATIONS.json --a /path/to/completed_A.json --b /path/to/completed_B.json --output /tmp/review_comparison.json
```

`prepare` expects precisely R001–R058 in order in EVIDENCE.md, 58 blank unique identities, and produces two identical blank JSON arrays and `manifest.json`. It never recomputes original source-record hashes from Markdown. `validate` prints a JSON report and returns nonzero on errors. A missing annotation is exactly `"annotator_identity":"", "annotated_at":"", "secondary_category":null, "evidence_note":""`. All other partial states are invalid. Dates must include a timezone. `compare` preserves both labels and notes; does not compute consensus or ASR. Outputs are exclusive-create; no overwrite. Different identity strings are not proof of independent annotation.

Policy categories: `explicit_text_refusal`, `summary_only`, `action_intent_without_valid_decision`, `incomplete_output`, `other_ambiguous`.
