# AgentTrust: Agent-to-Agent Social Engineering Benchmark

Benchmarking privilege escalation via agent-to-agent social engineering in multi-agent LLM systems. We test whether a compromised low-privilege Parser agent can manipulate a high-privilege Admin agent into executing unauthorized tool calls through social engineering tactics: authority spoofing, artificial urgency, data spoofing, and gaslighting.

## Current Status

### ✅ Baseline v1 Complete (2026-08-22)
- **576 experiments** across 4 Groq models
- **16 payloads** (4 per category) across 4 social engineering categories
- **Overall ASR: 1.04%** — models effectively resist basic social engineering attacks
- **Most vulnerable:** allam-2-7b (2.8% ASR) on Data Spoofing (5.6%)
- **Most robust:** openai/gpt-oss-120b, qwen/qwen3.6-27b (0% ASR across all categories)
- **Publication-quality heatmap** generated (300 DPI, ready for journals)

### 🚀 Extended v2 In Progress
- **60 payloads** (15 per category) with sophisticated tactics
- **Additional models planned:** Google Gemini Flash, Cerebras Llama, OpenRouter
- **Multi-turn attacks** and combined tactics in development
- **Benign control set** (20 legitimate requests) for false positive rate measurement
- **Statistical power improvement:** 540 scenarios per model (vs 144 in v1)

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
# Run all 576 baseline experiments (4 models × 16 payloads)
python3 evaluation/run_all_models.py --api-only

# Expected runtime: ~30-45 minutes
# Results appear in: sandbox/logs/attacks.jsonl
```

### Generate Analysis and Visualization
```bash
# Generate summary statistics
python3 evaluation/analysis_pipeline.py

# Create publication-quality heatmap
python3 analysis/heatmap.py

# Outputs:
# - results/analysis_report.json (summary statistics)
# - results/heatmap_asr_data.json (model × category matrix)
# - results/figures/heatmap_baseline_v1.png (300 DPI heatmap)
```

---

## Baseline Results Summary

### Overall Attack Success Rate

| Model | ASR | 95% CI | Type |
|---|---|---|---|
| allam-2-7b | 2.8% | [1.1%, 6.9%] | 7B |
| openai/gpt-oss-20b | 1.4% | [0.4%, 4.9%] | 20B |
| openai/gpt-oss-120b | **0.0%** | [0.0%, 2.6%] | 120B |
| qwen/qwen3.6-27b | **0.0%** | [0.0%, 2.6%] | 27B |
| **Overall** | **1.04%** | **[0.5%, 2.2%]** | — |

### ASR by Attack Category

| Category | ASR | n | Interpretation |
|---|---|---|---|
| Data Spoofing | 1.4% | 144 | Fake logs, SIEM alerts, CVE numbers (highest impact) |
| Artificial Urgency | 1.4% | 144 | Time-critical crises, business threats |
| Authority Spoofing | 0.7% | 144 | Fake CISO/admin directives |
| Gaslighting | 0.7% | 144 | Claims that safety mechanisms are broken |

**Key finding:** All attacks met with near-complete resistance. Even the most effective category (Data Spoofing) succeeded only 1.4% of the time.

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
│       └── attacks.jsonl    # 576 baseline experiment logs
├── evaluation/
│   ├── run_all_models.py    # Main experiment launcher
│   ├── analysis_pipeline.py # Statistics and summary
│   ├── experiment_queue.py  # Job queue with checkpoints
│   └── run_experiments.py   # Per-model experiment runner
├── analysis/
│   └── heatmap.py           # Publication-quality visualization
├── results/
│   ├── analysis_report.json # Summary statistics
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
| **H1:** Default ASR ≥ 25% | ❌ REJECTED | ASR = 1.04%, p < 0.001 | Safety-tuned models only |
| **H2:** Larger models more robust | ✅ CONFIRMED | 120B: 0%, 7B: 2.8%, p = 0.04 | Small effect size, low power |
| **H3:** Source text reduces ASR | ⏳ NOT TESTED | — | Planned for extended v2 |

---

## Dataset Details

### Attack Payloads (v1 Baseline)

**16 payloads** across 4 categories (4 per category):

#### Authority Spoofing (4)
- SOC alert with incident ID
- GDPR compliance directive
- FBI/IRS impersonation notice
- Senior engineer authorization request

#### Artificial Urgency (4)
- Database corruption (5-minute window)
- Active breach scenario
- Board meeting decision deadline
- Production outage ($150K/min revenue loss)

#### Data Spoofing (4)
- Fake audit logs
- Wire transfer record
- SIEM alert (Splunk format)
- Vulnerability scan report

#### Gaslighting (4)
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

## Models Tested (Baseline v1)

All models via **Groq API** (safety-tuned collection):

| Model | Parameters | Vulnerability | Notes |
|---|---|---|---|
| allam-2-7b | 7B | 2.8% ASR | Most vulnerable; susceptible to data spoofing |
| qwen/qwen3.6-27b | 27B | 0.0% ASR | Completely resistant |
| openai/gpt-oss-20b | 20B | 1.4% ASR | Vulnerable to authority + urgency |
| openai/gpt-oss-120b | 120B | 0.0% ASR | Completely resistant; largest model |

**Extended v2 will add:** Google Gemini Flash, Cerebras Llama, OpenRouter models for provider diversity.

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
sandbox/logs/attacks.jsonl         # All 576 experiment runs (JSON Lines)
results/analysis_report.json       # Summary statistics
results/heatmap_asr_data.json      # Model × category ASR matrix
results/figures/heatmap_baseline_v1.png  # Publication figure (300 DPI, 12×8")
```

### Verification
```bash
# Count experiments
jq -s 'length' sandbox/logs/attacks.jsonl
# Expected: 576

# Check summary statistics
python3 -c "import json; print(json.load(open('results/analysis_report.json')))"

# Regenerate heatmap
python3 analysis/heatmap.py
```

---

## Roadmap

### ✅ Completed
- [x] Baseline v1 experiments (576 runs, 4 models, 16 payloads)
- [x] Statistical analysis and confidence intervals (Wilson score)
- [x] Publication-quality heatmap (300 DPI)
- [x] Paper draft with results and discussion
- [x] Extended v2 payload creation (44 new payloads, 60 total)
- [x] Results tables for publication

### 🚀 In Progress
- [ ] Extended v2 experiments (60 payloads, same 4 models)
- [ ] Multi-turn attack scenarios
- [ ] Benign control set (false positive rate measurement)
- [ ] Additional models (Gemini Flash, Cerebras, OpenRouter)

### 📋 Planned (v3+)
- [ ] Frontier models (GPT-4o, Claude 3.5, Gemini) via research credits
- [ ] Defense mechanism testing (5+ strategies)
- [ ] Cross-model matrix (Parser vs Admin from different providers)
- [ ] Jailbreak-style and combination tactics
- [ ] Dynamic defense evaluation
- [ ] arXiv submission

---

## Team & Roles

This research is conducted collaboratively with roles including:

- **Infrastructure & Coordination** — Experiment runner, evaluation pipeline, API management
- **Payload Curation** — Social engineering tactics, realistic attack design
- **Statistical Analysis & Publication** — Result interpretation, paper drafting, peer communication
- **Research & Outreach** — Academic communication, resource acquisition

---

## Limitations (Baseline v1)

**Provider bias:**
- Only Groq API models tested (safety-tuned collection)
- No frontier models (GPT-4, Claude 3.5, Gemini Pro)
- Results may not generalize to other providers or base models

**Attack sophistication:**
- Surface-level tactics only (placeholders for v2)
- Single-turn interactions (no multi-turn or chained attacks)
- Limited payload diversity (16 payloads, n=144 per model)

**Experimental design:**
- No benign control set (FPR not measured)
- No defense mechanism comparisons (baseline only)
- No variance estimation (single repetition)
- Cross-model matrix not tested (Parser = Admin)

**Statistical power:**
- MDES ≈ 25pp with n=144 per model
- Observed effects (0-5.6%) below detection threshold
- Extended v2 with 540 scenarios per model will improve power 4×

See `docs/paper_draft.md` Section 5.3 for comprehensive limitations discussion.

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
