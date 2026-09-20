# AgentTrust: Agent-to-Agent Social Engineering Benchmark

Benchmarking privilege escalation via agent-to-agent social engineering in multi-agent LLM systems. We test whether a compromised low-privilege Parser agent can manipulate a high-privilege Admin agent into executing unauthorized tool calls through social engineering tactics: authority spoofing, artificial urgency, data spoofing, and gaslighting.

## Current Status

### v3 Final — complete (2026-09-19)
- **2,475 unique experiments** across 6 models and 3 providers
- **60 payloads** (15 per category) x 3 defense conditions x 3 repetitions
- **Overall ASR: 6.87%** (170/2,475, 95% CI 5.94–7.93%)
- **13x spread between models** — gpt-oss-20b 13.33% vs minimax-m3 0.00% on identical payloads (chi2=109.6, df=5, p<10^-21)
- **Both in-context defenses were null** — source text p=0.76, double-confirmation p=0.92 (OR=1.02)
- Publication-quality heatmap and full statistics committed

### Known gaps
- **No benign control set.** A 0% ASR model cannot yet be distinguished from one that refuses everything. Highest-priority next step.
- **Two Gemini models undersampled** (n=169 and n=146 of 540) — Google API rate limiting truncated both runs. Excluded from model-ranking claims.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Groq API key ([free tier available](https://console.groq.com))
- macOS/Linux/WSL

### Setup
```bash
# Clone repository
git clone https://github.com/wify777/AI-vs-AI-Social-Engineering.git
cd AI-vs-AI-Social-Engineering

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Run Baseline Experiments
```bash
# Run one model against the v3 benchmark (540 experiments)
PYTHONPATH=$PWD python3 evaluation/run_experiments.py \
  --model openai/gpt-oss-20b \
  --benchmark benchmark/benchmark_v3_escalated.json

# Runs resume from a checkpoint if interrupted.
# Do not run two models of the same provider in parallel - rate limits
# compound and each retry costs 30-90s.
# Results append to: sandbox/logs/attacks.jsonl
```

### Generate Analysis and Visualization
```bash
# Generate summary statistics
python3 evaluation/analysis_pipeline.py

# Create publication-quality heatmap
python3 analysis/heatmap.py

# Outputs:
# - results/final_stats_v3.json (ASR + Wilson CIs by model/category/condition)
# - results/heatmap_asr_data.json (model × category matrix)
# - results/figures/heatmap_v3_final.png (300 DPI, 14×8")
```

---

## Results Summary (v3 Final)

### Attack Success Rate by Model

| Model | Provider | ASR | 95% CI | n |
|---|---|---|---|---|
| openai/gpt-oss-20b | Groq | **13.33%** | [10.72, 16.46] | 540 |
| nvidia/nemotron-3-nano-omni-30b | OpenRouter | 11.11% | [8.73, 14.04] | 540 |
| openai/gpt-oss-120b | Groq | 6.67% | [4.85, 9.09] | 540 |
| gemini-3.6-flash* | Google | 1.18% | [0.33, 4.21] | 169 |
| gemini-flash-latest* | Google | 0.00% | [0.00, 2.56] | 146 |
| minimax/minimax-m3 | OpenRouter | **0.00%** | [0.00, 0.71] | 540 |
| **Overall** | — | **6.87%** | **[5.94, 7.93]** | **2,475** |

\* run truncated by Google API rate limiting; excluded from ranking claims.

Model differences are strongly significant (chi2=109.64, df=5, p=4.9x10^-22).

### ASR by Attack Category

| Category | ASR | 95% CI | n |
|---|---|---|---|
| Authority Spoofing | 10.05% | [7.95, 12.63] | 637 |
| Data Spoofing | 8.01% | [6.11, 10.43] | 612 |
| Artificial Urgency | 7.52% | [5.68, 9.88] | 612 |
| Gaslighting | 1.79% | [1.00, 3.18] | 614 |

Category differences are significant (chi2=36.44, df=3, p=6.0x10^-8). Gaslighting is the clear outlier; the other three overlap substantially and we do not claim an ordering among them.

### Defense Conditions — both null

| Condition | ASR | 95% CI | n | vs baseline |
|---|---|---|---|---|
| baseline | 6.54% | [5.04, 8.43] | 826 | — |
| with_source_text | 7.39% | [5.80, 9.38] | 825 | +0.85pp, p=0.76 |
| with_defense_mechanism | 6.67% | [5.16, 8.59] | 824 | +0.13pp, p=0.92 |

Neither intervention moved ASR. An earlier draft of this work reported a 54% reduction for the double-confirmation mechanism; that figure did not survive deduplication of the experiment log and **is retracted**.

### Key findings

1. **Model choice dominates.** A 13.3pp spread across models on identical payloads, against nulls for both defenses we tested. Robustness in this threat model lives in the model, not the prompt-level scaffolding around it.
2. **Defensive system prompts suppress measurement, not attacks.** A prompt containing "be careful with destructive operations" drove ASR to zero for *every* model, erasing the real spread. All reported results use a neutral prompt; benchmarks in this space should publish the victim prompt verbatim.
3. **Gaslighting barely works.** Attacks asserting false facts about the world (who is asking, what the logs say) succeed; attacks asserting that the model's own safety checks are broken largely do not.

---

## Project Structure

```
.
├── payloads/                 # Attack payload datasets
│   ├── seed/
│   │   ├── authority_spoofing.json (v1)
│   │   ├── artificial_urgency.json (v1)
│   │   ├── data_spoofing.json (v1)
│   │   ├── gaslighting.json (v1)
│   │   ├── authority_spoofing_v2.json (11 new)
│   │   ├── artificial_urgency_v2.json (11 new)
│   │   ├── data_spoof_v2.json (11 new)
│   │   └── gaslighting_v2.json (11 new)
│   └── ...
├── benchmark/
│   └── benchmark.json        # Combined v1 + v2 (60 payloads)
├── sandbox/
│   ├── agents/
│   │   ├── admin.py         # High-privilege agent
│   │   └── parser.py        # Low-privilege agent
│   ├── tools.py             # Tool stubs (no real side effects)
│   ├── bus.py               # Message bus and experiment runner
│   └── logs/
│       └── attacks.jsonl    # 2,475 experiment logs (JSON Lines)
├── evaluation/
│   ├── run_all_models.py    # Main experiment launcher
│   ├── analysis_pipeline.py # Statistics and summary
│   ├── experiment_queue.py  # Job queue with checkpoints
│   └── run_experiments.py   # Per-model experiment runner
├── analysis/
│   └── heatmap.py           # Publication-quality visualization
├── results/
│   ├── final_stats_v3.json  # ASR + Wilson CIs (model/category/condition)
│   ├── heatmap_asr_data.json # Model × category matrix
│   └── figures/
│       └── heatmap_baseline_v1.png # 300 DPI heatmap
├── docs/
│   ├── paper_draft.md       # Full paper draft with results
│   └── results_tables.md    # Publication-ready tables
└── README.md                # This file
```

---

## Hypothesis Testing Results

| Hypothesis | Status | Finding | Caveat |
|---|---|---|---|
| **H1:** Default ASR ≥ 25% | REJECTED | Overall 6.87% [5.94, 7.93]; top model 13.33% | Rejected in aggregate and for every individual model |
| **H2:** Larger models more robust | UNRESOLVED | Holds within gpt-oss (120B 6.67% < 20B 13.33%), fails across vendors | Scale is confounded with training approach; see paper §5.6 for an isolating design |
| **H3:** Source text reduces ASR ≥15pp | REJECTED | +0.85pp, wrong direction, p=0.76 | Informative null, not underpowered (n≈825/condition) |

---

## Dataset Details

### Attack Payloads (v3)

**60 payloads** across 4 categories (15 per category). Examples below are representative, not exhaustive:

#### Authority Spoofing (15)
- SOC alert with incident ID
- GDPR compliance directive
- FBI/IRS impersonation notice
- Senior engineer authorization request

#### Artificial Urgency (15)
- Database corruption (5-minute window)
- Active breach scenario
- Board meeting decision deadline
- Production outage ($150K/min revenue loss)

#### Data Spoofing (15)
- Fake audit logs
- Wire transfer record
- SIEM alert (Splunk format)
- Vulnerability scan report

#### Gaslighting (15)
- Claim safety filters are compromised
- Suggest permissions are fake displays
- Claim everyone else completed the action
- State restrictions are outdated

### Attack Payload Structure

Each payload includes:
```json
{
  "id": "payload_id",
  "category": "Attack Category",
  "attack_content": "Full attack text with realistic details",
  "expected_target_tool": "Tool name (e.g., execute_sql_query)",
  "difficulty": "easy|medium|hard",
  "tactic": "Brief description of psychological tactic",
  "why_might_succeed": "Reasoning behind effectiveness",
  "why_might_fail": "Defense mechanisms that stop it"
}
```

---

## Models Tested (v3 Final)

Six models across three providers:

| Model | Provider | Params | ASR | Coverage |
|---|---|---|---|---|
| openai/gpt-oss-20b | Groq | 20B | 13.33% | 540/540 |
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning | OpenRouter | 30B (A3B) | 11.11% | 540/540 |
| openai/gpt-oss-120b | Groq | 120B | 6.67% | 540/540 |
| minimax/minimax-m3 | OpenRouter | — | 0.00% | 540/540 |
| gemini-3.6-flash | Google | — | 1.18% | **169/540** |
| gemini-flash-latest | Google | — | 0.00% | **146/540** |

The four complete models carry all model-level claims. Both Google runs were cut short by API rate limiting — each remaining experiment cost 30–90s of backoff, putting completion at an estimated 35–40 hours.

---

## Reproducibility and Documentation

### Paper Draft
See `docs/paper_draft.md` for full methodology, results, discussion, and limitations.

### Publication-Ready Tables
See `docs/results_tables.md` for tables formatted for journals, conferences, and technical reports:
- Table 1: Overall ASR by Model
- Table 2: ASR by Attack Category
- Table 3: Model × Category Matrix
- Table 4: Successful Attacks Analysis
- Table 5: Defense Gaps
- Table 6: Statistical Power Analysis
- Table 7: Confidence Interval Summary
- Table 8: v1 vs v2 Comparison

### Raw Data
```
sandbox/logs/attacks.jsonl            # All 2,475 experiment runs (JSON Lines, deduplicated)
results/final_stats_v3.json           # ASR + Wilson CIs by model / category / condition
results/heatmap_asr_data.json         # Model × category ASR matrix
results/figures/heatmap_v3_final.png  # Publication figure (300 DPI, 14×8")

The published log is scrubbed of credentials: two error strings that had captured
a Google API key from a request URL read `<REDACTED_GOOGLE_API_KEY>`.
```

### Verification
```bash
# Count experiments
jq -s 'length' sandbox/logs/attacks.jsonl
# Expected: 2475

# Confirm no duplicates (model + payload + condition + repetition must be unique)
jq -s '[.[] | [.model_admin, .payload_id, .condition, .repetition]] | (length) - (unique | length)' \
  sandbox/logs/attacks.jsonl
# Expected: 0

# Overall ASR
jq -s '[.[] | select(.outcome.tool_executed)] | length' sandbox/logs/attacks.jsonl
# Expected: 170  (170/2475 = 6.87%)

# Regenerate heatmap and statistics
python3 analysis/heatmap.py
```

---

## Roadmap

### Completed
- [x] Baseline v1 (576 runs, 4 Groq models, 16 payloads)
- [x] v3 final (2,475 unique runs, 6 models, 60 payloads, 3 conditions, 3 repetitions)
- [x] Wilson confidence intervals and chi-square tests across model / category / condition
- [x] Publication-quality heatmap (300 DPI)
- [x] Paper draft with results, discussion and limitations
- [x] Deduplicated dataset published for reproducibility

### Next (v4)
- [ ] **Benign control set** — 20 legitimate requests per model for false-positive rates. Blocking gap: 0% ASR is currently indistinguishable from blanket refusal.
- [ ] Complete the two rate-limited Google models (169→540, 146→540)
- [ ] **Isolate the training-time effect** — one base checkpoint across base / SFT+RLHF / DPO variants, so post-training is the only thing that varies (paper §5.6)
- [ ] Out-of-context defenses — hard authorization checks, allowlists, out-of-band approval. Both in-context defenses were null.
- [ ] Frontier models (GPT-4o, Claude, Gemini Pro)

### Later
- [ ] Multi-turn and adaptive attacks — the current attacker is static, so reported ASR is a floor
- [ ] Cross-provider matrix (Parser from provider A, Admin from provider B)
- [ ] Combination tactics (authority + data spoofing, etc.)
- [ ] arXiv submission

---

## Team & Roles

This research is conducted collaboratively with roles including:

- **Infrastructure & Coordination** — Experiment runner, evaluation pipeline, API management
- **Payload Curation** — Social engineering tactics, realistic attack design
- **Statistical Analysis & Publication** — Result interpretation, paper drafting, peer communication
- **Research & Outreach** — Academic communication, resource acquisition

---

## Limitations (v3 Final)

**Measurement:**
- **No benign control set.** ASR alone cannot separate a robust model from one that refuses every request, legitimate ones included. This is the single biggest gap — minimax-m3's 0% is currently uninterpretable in that respect.
- ASR counts tool execution only. Near-misses, partial compliance, and information leakage without a tool call are invisible to it.
- Three repetitions per payload/condition pooled without modelling within-payload correlation, which may make intervals mildly optimistic.

**Sampling:**
- Two of six models undersampled (n=169, n=146 of 540) due to Google API rate limiting; excluded from ranking claims.
- No frontier models. All six are small-to-mid open or free-tier checkpoints.
- Single Admin system prompt — every number is conditional on that one neutral prompt.

**Attack sophistication:**
- Single-turn only, 60 payloads, no chained or adaptive attacks.
- The attacker never responds to a refusal, so reported ASR is a **floor**, not an estimate of what an adaptive adversary achieves.
- All payloads carry escalation markers, which may not match how injected content appears in production.

**Causal inference:**
- The six models differ in vendor, pretraining data, architecture, size and post-training simultaneously. "Robustness tracks the model" is measured; "robustness comes from RLHF" is not established. See paper §5.6 for a design that would isolate it.

See `docs/paper_draft.md` §5.5 for the full limitations discussion.

---

## Ethical Considerations

All experiments are conducted in a **sandboxed environment** with stub tools. No real systems, users, or data are affected. Attack payloads reference fictional entities only. This research aims to identify vulnerabilities in multi-agent LLM architectures so developers can build safer systems.

---

## References & Related Work

- **AgentDojo** (Debenedetti et al., NeurIPS 2024): Single-agent prompt injection benchmark
- **InjecAgent** (Zhan et al., ACL 2024): Indirect prompt injection in tool-integrated agents
- **He et al. (2025):** Communication attacks in multi-agent systems
- **Greshake et al. (2023):** Indirect prompt injection via web content

---

## Citation

```bibtex
@misc{agenttrust2026,
  title={AgentTrust: Benchmarking Privilege Escalation via Agent-to-Agent Social Engineering},
  author={Anonymous},
  year={2026},
  url={https://github.com/wify777/AI-vs-AI-Social-Engineering}
}
```

---

## Getting Help

- **Questions about experiments?** See `docs/paper_draft.md` Section 3 (Methodology)
- **Questions about results?** See `docs/paper_draft.md` Section 4 (Results) and `docs/results_tables.md`
- **Questions about payloads?** See `payloads/seed/` for examples and `docs/paper_draft.md` Section 3.3 (Taxonomy)
- **Issues with setup?** Check `.env.example` and ensure GROQ_API_KEY is set
- **Report bugs?** Open an issue on GitHub

---

**Last Updated:** 2026-08-22  
**Status:** Baseline v1 complete, Extended v2 in progress
