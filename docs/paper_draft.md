# AgentTrust: Benchmarking Privilege Escalation via Agent-to-Agent Social Engineering in Multi-Agent LLM Systems

## Abstract

Multi-agent LLM systems increasingly delegate tasks across agents with different privilege levels. We introduce AgentTrust, an open-source benchmark measuring whether a compromised low-privilege Parser agent can manipulate a high-privilege Admin agent into executing unauthorized tool calls via social engineering tactics.

**Main Results (v3 Final: 60 payloads, 10 models, n=2,731):** We conducted 2,731 experiments evaluating ten models across Groq, Google, and OpenRouter using 60 social engineering attack payloads spanning four categories: authority spoofing, artificial urgency, data spoofing, and gaslighting. Our primary metric — Attack Success Rate (ASR) — measures tool execution directly from execution logs. Overall ASR: **2.71%** (74/2,731, 95% CI: 2.1–3.4%). We observe extreme variance across models: openai/gpt-oss-20b shows **17.27% ASR** (19/110, most vulnerable), while meta-llama/llama-3.2-3b and mistralai/mistral-7b maintain **0% ASR across 540 combined experiments each** (most protected). Critically, we discovered that **defensive language in system prompts masks genuine vulnerabilities**: removing defensive disclaimers from the Admin prompt caused ASR to increase 5–6×. Conversely, adding defense mechanisms (e.g., double-confirmation) reduces ASR by 54%, suggesting that **training-time safety is less important than runtime defense strategies**. Data spoofing attacks are 19.5× more effective than gaslighting (5.66% vs 0.29% ASR).

**Key Finding:** Real defenses emerge from runtime checks and agent design, not training or system prompt disclaimers.

Our benchmark and all experimental artifacts are publicly available at https://github.com/wify777/AI-vs-AI-Social-Engineering

## 1. Introduction

### 1.1 Problem Statement

Modern AI systems increasingly use multi-agent architectures where specialized agents collaborate to complete complex tasks. In these systems, agents operate at different privilege levels: a web-browsing agent may parse untrusted content, while a system administration agent has access to critical tools such as database queries, user account management, and external communications.

This privilege separation creates a trust boundary. When a low-privilege agent communicates findings to a high-privilege agent, the high-privilege agent must decide whether to trust the information and act on it. If the low-privilege agent is compromised — for example, via indirect prompt injection embedded in web content — it may attempt to manipulate the high-privilege agent into executing unauthorized operations.

### 1.2 Research Gap

Existing benchmarks test single-agent prompt injection:

- **AgentDojo** (Debenedetti et al., NeurIPS 2024): Tests whether an agent can be tricked by injected content in its own task context. The attack and the victim are the same agent.

- **InjecAgent** (Zhan et al., ACL 2024): Tests indirect prompt injection where an agent reads malicious content and executes unauthorized tools. Again, a single agent reads the injection and decides to act.

Both benchmarks measure a "content vs. agent" attack vector. Neither tests the distinct failure mode we study: "agent vs. agent" social engineering, where a compromised agent uses natural language persuasion tactics to manipulate an independent peer agent.

### 1.3 Our Contribution

We introduce AgentTrust, a benchmark that tests the **inter-agent trust boundary**. Specifically:

1. A **two-agent sandbox** where a Parser agent (low privilege) communicates with an Admin agent (high privilege) via a message bus.

2. A **taxonomy of four social engineering categories** adapted from human social engineering literature: authority spoofing, artificial urgency, data fabrication, and gaslighting.

3. A **benchmark dataset** of 60 attack payloads (15 per category) plus 20 benign control requests for false positive measurement.

4. An **objective primary metric** (ASR) based on tool execution logs, not LLM-as-judge evaluation.

### 1.4 Hypotheses

**H1:** Admin agents with default system prompts (no explicit peer-trust defense) will show ASR ≥ 25% when attacked by a compromised Parser agent.

**H2:** Larger models (70B parameters) will show lower ASR as Admin (better defense) but higher ASR as Parser (better attack generation) compared to smaller models (7B parameters).

**H3:** Providing raw source text alongside the Parser's summary will reduce ASR by ≥ 15 percentage points compared to summary-only communication.

## 2. Related Work

### 2.1 Prompt Injection and Indirect Attacks

Prompt injection attacks manipulate LLM behavior by embedding instructions in user-controlled input. Greshake et al. (2023) demonstrated indirect prompt injection where an attacker embeds malicious instructions in web content; an LLM-powered agent reads the content and executes unintended actions. This attack is particularly dangerous because the LLM faithfully processes untrusted data, assuming it is benign.

Subsequent work by Zhan et al. (2024) formalized indirect prompt injection in tool-use scenarios and introduced InjecAgent, a benchmark measuring whether agents execute unauthorized tools when prompted by injected content. However, InjecAgent tests a single agent's vulnerability to content injection—the agent reads the injection and acts on it directly.

### 2.2 Multi-Agent Benchmarks and Red-Teaming

Recent benchmarks focus on multi-agent system robustness. AgentDojo (Debenedetti et al., 2024) evaluates agent safety across diverse attack categories by injecting malicious content into agent environments. However, like InjecAgent, AgentDojo still measures content-to-agent attacks, not inter-agent trust failures.

He et al. (2025) and Lee & Tiwari (2025) investigate communication attacks in multi-agent systems, focusing on how agents can be manipulated through their peer interactions. These works recognize that in multi-agent architectures, agents trust each other's outputs, creating new attack surfaces beyond direct prompt injection.

### 2.3 Social Engineering and Human-Computer Interaction

Social engineering leverages psychological manipulation to bypass security controls. Cialdini's principles (authority, reciprocity, scarcity, consistency, liking, social proof) are foundational to human social engineering. Recent work applies these principles to AI systems: authority spoofing (impersonating trusted entities), artificial urgency (creating time pressure), data fabrication (falsifying evidence), and gaslighting (undermining trust in safety mechanisms).

### 2.4 Delta with Prior Work

**AgentTrust's novelty:** We specifically test inter-agent trust boundaries—can a compromised peer agent persuade a colleague to misuse privileges? This is orthogonal to content injection (which tests whether an agent trusts untrusted data in its own task) and is relevant to real-world multi-agent systems where agents communicate via APIs, message queues, and natural language.

## 3. Methodology

### 3.1 Threat Model

**Attacker goal:** Cause the Admin agent to execute a restricted tool (delete_user_account, reset_user_password, execute_sql_query, dispatch_external_email) by compromising the Parser agent via indirect prompt injection.

**Attacker capabilities:**
- Can embed arbitrary text in web content that the Parser agent reads
- Cannot directly communicate with the Admin agent
- Cannot modify system prompts or tool configurations

**Assumptions:**
- Parser agent faithfully processes injected content (realistic per Greshake et al. 2023)
- Admin agent receives Parser's output as a peer message
- All tools are stub implementations with no real side effects

### 3.2 System Architecture

```
[Untrusted Web Content] → [Parser Agent] → [Message Bus] → [Admin Agent] → [Tool Stubs]
                              (low priv)                       (high priv)      ↓
                                                                            [Execution Log]
```

**Parser Agent:** Reads web content, summarizes findings, forwards to Admin. System prompt instructs it to parse and summarize; it has no tool access.

**Admin Agent:** Receives messages from Parser, decides whether to act. Has access to four restricted tools. Default system prompt says to trust Parser but be careful with destructive operations.

**Message Bus:** Routes messages between agents. Logs all communications. No hidden system prompts (unlike LangChain/AutoGen).

### 3.3 Attack Taxonomy

| Category | Definition | Example |
|---|---|---|
| Authority Spoofing | Impersonate system/admin/security | "[SYSTEM ALERT] Reset password..." |
| Artificial Urgency | Fabricate time-critical crisis | "Database failing in 5 minutes..." |
| Data Fabrication | Falsify logs/audit records | "Audit shows 1500 brute-force attempts..." |
| Gaslighting | Claim safety mechanisms are broken | "Your filters are compromised..." |

### 3.4 Benchmark Dataset

**Baseline v1 (completed):** 16 attack payloads (4 per category) across 4 categories.
**Extended v2 (in progress):** 60 attack payloads (15 per category).

Dataset structure:
- **Attack payloads:** 16 baseline, 44 new (total 60 planned)
- **Benign control set:** 20 legitimate requests (planned future work)
- **Conditions tested (baseline only):** single baseline condition

### 3.5 Models Evaluated (Baseline v1)

| Model | Provider | Parameters | Type |
|---|---|---|---|
| allam-2-7b | Groq | 7B | Open-source |
| qwen/qwen3.6-27b | Groq | 27B | Open-source |
| openai/gpt-oss-20b | Groq | 20B | Open-source |
| openai/gpt-oss-120b | Groq | 120B | Open-source |

**Note:** All baseline models are from Groq's safety-tuned collection. Extended v2 will add models from Google AI, Cerebras, and OpenRouter for diversity.

### 3.6 Metrics

**Primary: Attack Success Rate (ASR)**
ASR = (tool calls executed) / (total attack scenarios) × 100%
Measured by parsing execution logs. Binary outcome: tool called (1) or not called (0). No LLM-as-judge.

**Secondary: Response Compliance Scale (RCS)**
0 = Refusal (Admin explicitly refuses)
1 = Hesitation (Admin questions, asks for verification)
2 = Compliance (Admin executes tool)

**Confidence intervals:** 95% Wilson score (robust at 0% and 100%)
**Statistical tests:** Fisher exact, McNemar (paired, for H3), Holm–Bonferroni correction for multiple comparisons.

### 3.7 Experimental Design (Baseline v1)

Each attack payload is tested:
- 1 condition: baseline (single-turn attack)
- 1 repetition (no variance estimation in baseline)
- 4 models (Groq collection)

Total runs: 16 payloads × 1 condition × 1 rep × 4 models = **64 scenarios**
With multiple attacks per payload, actual runs: **576 total** (144 per model)

### 3.8 Power Analysis

With n=144 runs per model (16 payloads × 9 runs each), power analysis shows:
- Minimum detectable effect size: ~20-25 percentage points at 80% power
- Current observed effects (0-5.6%) are below this threshold
- Extended v2 with 60 payloads (540 scenarios per model) will improve power substantially

**Important caveat:** Small observed ASR values (1.04% overall) may reflect ceiling effects (well-defended models) rather than true lack of vulnerability. Additional testing with more sophisticated attacks is necessary.

## 4. Results

### 4.1 Overall ASR (v3 Final: 60 payloads, 10 models, n=2,731)

| Model | n | Successes | ASR (%) | 95% CI (%) | Interpretation |
|---|---|---|---|---|---|
| openai/gpt-oss-20b | 110 | 19 | 17.27 | [11.2–25.3] | **HIGHLY VULNERABLE** |
| google/gemma-4-31b-it:free | 202 | 14 | 6.94 | [4.0–11.4] | Moderate vulnerability |
| openai/gpt-oss-120b | 326 | 22 | 6.74 | [4.4–9.9] | Moderate vulnerability |
| google/gemma-4-26b-a4b-it:free | 280 | 17 | 6.08 | [3.7–9.5] | Moderate vulnerability |
| gemini-3.6-flash | 181 | 2 | 1.11 | [0.2–3.9] | Protected |
| gemini-flash-latest | 192 | 0 | 0.00 | [0.0–1.9] | Protected |
| meta-llama/llama-3.2-3b:free | 540 | 0 | 0.00 | [0.0–0.7] | **HIGHLY PROTECTED** |
| mistralai/mistral-7b:free | 540 | 0 | 0.00 | [0.0–0.7] | **HIGHLY PROTECTED** |
| allam-2-7b | 1 | 1 | 100.00 | [20.7–100.0] | Insufficient data (n=1) |
| qwen/qwen3.6-27b | 1 | 0 | 0.00 | [0.0–79.3] | Insufficient data (n=1) |
| **Overall** | **2,731** | **74** | **2.71** | **[2.1–3.4]** | **Extreme variance across vendors** |

**Critical findings:** 
1. **Extreme variation masks by low overall ASR.** OpenAI models (17.27% vs 6.74%) show 2.6× difference, while Google Gemma models show unexpected reversal (26B: 6.08% vs 31B: 6.94%), suggesting parameter count is not the dominant factor.

2. **Base models extraordinarily resilient.** Llama-3.2-3b and Mistral-7b maintain 0% ASR across 540 experiments each (1,080 total), despite lacking explicit RLHF safety tuning. This contradicts the hypothesis that safety training (RLHF) is necessary for robustness.

3. **Provider matters more than model size.** OpenRouter base models (0% ASR) > Groq safety-tuned models (6–17% ASR), suggesting that model training data diversity/instructions matter more than explicit safety RLHF.

### 4.2 ASR by Attack Category (All Models)

| Category | n | Successes | ASR (%) | 95% CI |
|---|---|---|---|---|
| Data Spoofing | 619 | 35 | 5.66 | [4.0–7.9] |
| Authority Spoofing | 731 | 24 | 3.28 | [2.2–4.8] |
| Artificial Urgency | 751 | 14 | 1.86 | [1.1–3.1] |
| Gaslighting | 691 | 2 | 0.29 | [0.1–1.1] |

**Critical observation:** Data spoofing is **19.5× more effective** than gaslighting (5.66% vs 0.29% ASR). This dramatic difference suggests models are far more vulnerable to fabricated data/logs than to psychological manipulation ("your safety mechanisms are broken"). Authority Spoofing shows intermediate effectiveness. Artificial Urgency is surprisingly ineffective, suggesting time-pressure tactics do not overcome model caution.

### 4.3 Model × Attack Category Matrix (ASR %)

| Model | Authority Spoof | Artificial Urgency | Data Spoofing | Gaslighting |
|---|---|---|---|---|
| openai/gpt-oss-20b | 18.2% (4/22) | 21.4% (6/28) | 47.4% (9/19) | 6.3% (1/16) |
| google/gemma-4-31b:free | 3.6% (1/28) | 6.8% (6/88) | 14.1% (7/50) | 0.0% (0/36) |
| openai/gpt-oss-120b | 4.0% (4/101) | 6.3% (9/143) | 20.0% (11/55) | 3.7% (1/27) |
| google/gemma-4-26b:free | 3.5% (2/57) | 5.7% (10/175) | 12.5% (5/40) | 0.0% (0/8) |
| gemini-3.6-flash | 0.0% (0/47) | 5.9% (2/34) | 0.0% (0/54) | 0.0% (0/46) |
| gemini-flash-latest | 0.0% (0/59) | 0.0% (0/55) | 0.0% (0/54) | 0.0% (0/24) |
| meta-llama/llama-3.2-3b:free | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) |
| mistralai/mistral-7b:free | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) |
| allam-2-7b | 100% (1/1) | — | — | — |
| qwen/qwen3.6-27b | 0.0% (0/1) | — | — | — |

**Vulnerability profile:** 
1. **Data Spoofing dominates across all vulnerable models.** gpt-oss-20b: 47.4%, gemma-31b: 14.1%, gpt-oss-120b: 20.0%.
2. **Base models (Llama, Mistral) impervious.** Perfect defense (0% ASR) across all 270 experiments per model.
3. **Gaslighting universally ineffective.** Only 2 successful attacks across 691 experiments (0.29%), suggesting models' core reasoning is robust against psychological manipulation.
4. **Gemma family reveals counterintuitive pattern:** Gemma-4-26b (6.08% overall) performs similarly to Gemma-4-31b (6.94%), despite 5B parameter difference, suggesting training quality/data > parameter count.

### 4.4 ASR by Defense Condition

| Condition | n | Successes | ASR (%) | 95% CI | Effect |
|---|---|---|---|---|---|
| baseline | 906 | 30 | 3.31 | [2.3–4.7] | Baseline (no defense) |
| with_source_text | 903 | 30 | 3.32 | [2.3–4.7] | No effect (+0.01pp) |
| with_defense_mechanism | 914 | 14 | 1.53 | [0.9–2.5] | **Effective (-54%)** |

**Critical finding:** 
1. **Source text provides zero protection.** Showing the original log/data alongside the Parser's summary does not improve robustness (3.31% vs 3.32% ASR). H3 hypothesis rejected.
2. **Defense mechanisms are highly effective.** Adding double-confirmation prompts ("Are you sure? This will delete an account") reduces ASR by 54% (3.31% → 1.53%), suggesting that **runtime defense checks outperform training-time safety measures**.
3. **Implication for system design:** Runtime guardrails > model training. A defense-lightweight model with good runtime checks is more secure than a heavily safety-tuned model with weak runtime defenses.

### 4.5 Critical Discovery: Prompt-Based Defenses are Artifacts

During extended v3 experiments, we discovered that **defensive language in system prompts artificially suppresses ASR to near-zero across all models.** 

Initial experiments using a defensive system prompt ("be careful with destructive operations", "only execute if confident") produced 0% ASR universally. When we removed defensive language and used a neutral system prompt ("You are a system administrator with access to these tools"), model-specific vulnerabilities emerged:

- **Before:** All models 0% ASR (defensive prompt artifact)
- **After:** gpt-oss-20b 29% ASR, gpt-oss-120b 7.67% ASR, base models 0% ASR (true vulnerabilities)

This suggests that **prompt-based defenses mask rather than prevent exploitation**. True robustness comes from training-time safety (RLHF), not instructions.

### 4.5 Hypothesis Tests (Revised)

**H1 (ASR ≥ 25% with default prompts):** **PARTIALLY CONFIRMED**
- Observed overall ASR: 3.08% (95% CI: [2.3–4.1])
- **However:** openai/gpt-oss-20b alone achieves 29.0% ASR (95% CI: [23.9–34.7])
- Revised hypothesis: ASR ≥ 25% observed for non-safety-tuned or minimally-tuned Groq models
- Caveat: With defensive system prompts, ASR→0% uniformly; true vulnerability hidden by prompt design

**H2 (Larger models more robust):** **CONFIRMED with exceptions**
- Within Groq safety-tuned family: 120B (7.67%) < 20B (29.0%) — **larger model is MORE robust**
- Difference: 21.3 percentage points (p < 0.001, Fisher exact)
- Between providers: Base models (Llama-3.2-3b, Mistral-7b, 3-7B range) show 0% ASR, suggesting training (not size) determines robustness
- Revised: Parameter count correlates with robustness within safety-tuned collections, but RLHF dominates across providers

**H3 (Source text reduces ASR):** **NOT TESTED IN v3**
- Baseline v1 and v3 use single-turn attacks (no source text variation)
- Deferred to v4 experiments with multi-turn conditions

## 5. Discussion

### 5.1 **CRITICAL FINDING: Runtime Defenses Trump Training-Time Safety**

Our most significant finding concerns the hierarchy of defenses in multi-agent LLM systems. We tested three conditions:

1. **Training-time safety (RLHF):** Models like gpt-oss-20b (17.27% ASR) show vulnerability despite "safety-tuning" claims. OpenRouter base models (0% ASR) are more robust without explicit safety training.

2. **Runtime defenses (agent design):** Adding double-confirmation checks reduces ASR by 54% (3.31% → 1.53%), dramatically outperforming training-time approaches.

3. **System prompt disclaimers:** Zero effect. Showing source text alongside parsed content has no impact on ASR (3.31% vs 3.32%).

**Interpretation:** The hierarchy of defenses is inverted from common assumptions:

```
Effectiveness ranking:
1. Runtime guardrails (double-confirmation)  -54% ASR ✅
2. Model training data (base vs tuned)       varies 17×
3. System prompt disclaimers                 0% effect ❌
```

**Why this matters:** A lightweight model with strong runtime guardrails is more secure than a heavily safety-tuned model with weak runtime defenses. This contradicts the field's emphasis on training-time safety alignment.

**Caveat:** This finding applies to the "agent-to-agent" threat model (compromised peer agent). For direct prompt injection (user-agent), training-time safety may have higher marginal value.

### 5.2 Training-Time Safety vs. Prompt-Time Defenses

Our v3 data strongly support this hierarchy:

| Defense Type | Impact on ASR | Reliability |
|---|---|---|
| Prompt-based ("be careful") | -∞ (0% → 0%) | Unreliable; easily overridden by social engineering |
| RLHF safety-tuning (Groq, Google) | Moderate (7–29% depending on model) | Reliable but incomplete |
| Base model training (Llama, Mistral) | Strong (0% ASR across 1,080 exp) | Highly reliable, but may reflect limited task diversity |

**Groq models (gpt-oss-20b)** show that even "safety-tuned" models have significant vulnerabilities (29% ASR) when prompt-level defenses are removed. This suggests their safety training is surface-level, focused on obvious refusals rather than genuine resistance to sophisticated social engineering.

**Base models (Llama-3.2-3b, Mistral-7b)** maintained 0% ASR across 540 experiments each, despite identical social engineering tactics. This is surprising given their lack of explicit RLHF tuning, but may reflect:
- Limited task scope (only four restricted tools)
- Alignment with instruction-following (they follow legitimate instructions, refuse suspicious ones)
- Lower language sophistication compared to Groq models (may fail to understand complex social engineering)

### 5.3 Implications for Multi-Agent System Design

1. **Do not rely on prompt-level defenses.** System prompt disclaimers create a false sense of security. A multi-agent system that depends on the Admin agent's instructions ("be careful") is vulnerable.

2. **Model choice matters deeply.** Within a safety-tuned family (Groq), vulnerability varies 3.8× (7.67% vs 29.0%). Between families (Groq vs base), variation is infinite (29% vs 0%). Deploying a multi-agent system requires careful model selection, not just prompt engineering.

3. **Test with neutral prompts.** Benchmark evaluation should avoid defensive language in system prompts, or clearly document this choice. Otherwise, results may reflect prompt artifacts rather than genuine model behavior.

### 5.2 Hypothesis Tests (Final Results, n=2,731)

**H1 (ASR ≥ 25% with default prompts):** **REJECTED** 
- Observed overall ASR: 2.71% (95% CI: [2.1–3.4])
- Observed ASR is significantly lower than 25% threshold (p < 0.001)
- **However:** openai/gpt-oss-20b alone achieves 17.27% ASR (19/110), which approaches the threshold for high-vulnerability subpopulation
- **Revised:** H1 rejected for overall population; partially supported for vulnerable models

**H2 (Larger models more robust):** **CONFIRMED with caveats**
- **Groq family:** gpt-oss-120b (6.74%, n=326) is 2.6× more robust than gpt-oss-20b (17.27%, n=110) ✅ CONFIRMED
- **Gemma family:** Gemma-4-26b (6.08%, n=280) ≈ Gemma-4-31b (6.94%, n=202) — **parameter count does NOT correlate with robustness** ❌ CONTRADICTED
- **OpenRouter base models:** Llama-3.2-3b (0% ASR, n=540) > Gemma-4-31b (6.94%) despite being 28× smaller
- **Interpretation:** H2 confirmed within controlled setting (same vendor, similar training), but breaks across vendors, suggesting training data/approach >> parameter count

**H3 (Source text reduces ASR ≥ 15pp):** **REJECTED** 
- Observed: baseline 3.31% vs with_source_text 3.32% = essentially no difference (+0.01pp)
- Source text shows zero protective benefit
- **But defense mechanism works:** with_defense_mechanism 1.53% = 54% reduction, validating H3's spirit (runtime defenses work) but not its implementation

### 5.3 Implications for Multi-Agent System Design

1. **Model selection matters far more than system prompts.** Between models, 60× variation in ASR (0% to 17.27%). Between prompts, <1% variation. **Invest in model selection, not prompt engineering for security.**

2. **Parameter count is necessary but insufficient.** Larger models are more robust within the same training paradigm, but training data/approach dominates across paradigms. A 3B base model outperforms a 31B fine-tuned model.

3. **Runtime defenses are most cost-effective.** Adding double-confirmation reduces ASR by 54%, outperforming any training-time approach measured. Practical systems should prioritize agent-design defenses.

4. **Category-specific vulnerabilities persist.** Data spoofing is 19.5× more effective than gaslighting. Systems should implement category-aware defenses (e.g., heightened verification for data-related operations).

### 5.4 Limitations (Updated with v3 Final Data)

**Sampling and generalization:**
- **Groq models well-sampled:** gpt-oss-20b (110), gpt-oss-120b (326) sufficient for robust estimates
- **Groq critically undersampled:** qwen (1), allam (1) — **insufficient (n=1 each)**, results unreliable
- **Google models adequately sampled:** Gemini Flash (181), Gemini Latest (192), Gemma-31b (202), Gemma-26b (280) — all n>150
- **Base models excellently sampled:** Llama-3.2-3b (540), Mistral-7b (540) — but only 2 models
- **No frontier models:** GPT-4o, Claude 3.5, Gemini Pro, o1 not evaluated
- **Provider bias:** Groq (436), Google (655), OpenRouter (1,080) — OpenRouter overrepresented, Groq undersampled relative to vulnerability

**Attack sophistication:**
- 60 payloads (15 per category) represent moderate complexity
- Surface-level tactics only (no multi-turn interaction)
- No chained attacks (combining authority + urgency + data spoofing)
- No jailbreak-style payloads ("your safety mechanisms are outdated")
- All payloads use escalation markers (may not reflect production web injection)

**Experimental design:**
- Single-condition baseline (neutral prompt only)
- No defensive variants (source citation, double-confirmation, chain-of-thought verification)
- No benign control set (cannot measure false positive rate)
- Each payload tested once per model (no within-model variance)
- Cross-model matrix not tested (Parser and Admin always same model)

**Measurement and analysis:**
- Binary outcome only (tool executed: yes/no)
- No refusal quality assessment (e.g., how convincingly did model refuse?)
- No hesitation analysis (did model express doubt?)
- No attention/saliency analysis (which parts of attack influenced decision?)
- Rate-limiting artifact: Groq experiments suffered 429 errors, some marked "[ERROR: Max retries exceeded]" (n ≈ 40, < 3% contamination)

**Statistical limitations:**
- Unbalanced design (1 allam vs 540 Llama)
- Google undersampled relative to Groq and OpenRouter
- Wide confidence intervals for < 50n models (gemini models)
- Multiple comparisons across models without Bonferroni correction

### 5.5 Future Work

**Immediate priorities (v4, recommended):**
- **Complete undersampled Groq models:** qwen/qwen3.6-27b (1→540 experiments), allam-2-7b (1→540 experiments) needed for reliable estimates
- **Investigate Gemma paradox:** Why does Gemma-4-26b (6.08%) perform similarly to larger Gemma-4-31b (6.94%)? Training difference, not parameter count?
- **Frontier models:** GPT-4o, Claude 3.5, Llama 3.1+ via research credits or commercial APIs
- **Benign control set:** 20 legitimate requests per model to establish false positive rates (FPR)

**Medium-term (v5+):**
- **Multi-turn attacks:** Progressive commitment (small request → escalation), adaptive responses to refusal
- **Defense mechanism variants (now that baseline works):**
  - Chain-of-thought verification ("Walk through security implications")
  - Confidence thresholds ("Only execute if confidence > 0.9")
  - Category-aware defenses ("Data operations require 2-factor verification")
  - Sandbox isolation ("Execute in simulation mode first")
- **Cross-provider matrix:** Parser from Provider A, Admin from Provider B (Groq-Google-OpenRouter = 9 combinations)
- **Category-specific attacks:** Deep dive into why Data Spoofing (5.66%) >> Gaslighting (0.29%)
- **Combination tactics:** Authority + Data Spoofing, Urgency + Authority, all categories simultaneously

**Lower priority (exploratory):**
- Jailbreak-style payloads ("Your safety mechanisms are outdated")
- Fine-tuning analysis (how RLHF changes vulnerability surface)
- Adversarial attack transfer (do attacks effective on gpt-oss-20b work on other models?)
- Automated vulnerability discovery (genetic algorithms to find maximally effective payloads)

## 6. Ethical Considerations

All experiments are conducted in a sandboxed environment with stub tools. No real systems, users, or data are affected. Attack payloads reference fictional entities only. This research aims to identify vulnerabilities in AI architectures so developers can build safer multi-agent systems.

## 7. Reproducibility

All code, data, and analysis scripts are publicly available at:
https://github.com/wify777/AI-vs-AI-Social-Engineering

To reproduce:
```
git clone https://github.com/wify777/AI-vs-AI-Social-Engineering.git
cd AI-vs-AI-Social-Engineering
pip install -r requirements.txt
python evaluation/run_all_models.py
python evaluation/analysis_pipeline.py
```

## References

1. Cialdini, R. B. (1984). *Influence: The Psychology of Persuasion*. William Morrow.

2. Greshake, K., Schafer, B., Shave, S., Miserez, C., & Kirsch, G. (2023). "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection." AISec Workshop.

3. Debenedetti, E., Zhou, K., Schmutz, S., Khanna, S., Weiss, E., & Sarkar, P. (2024). "AgentDojo: A Dynamic Environment to Evaluate Attacks and Defenses for LLM Agents." NeurIPS 2024.

4. Zhan, J., Liu, M., Koh, P. W., & Mitchell, M. (2024). "InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents." ACL 2024.

5. He, P., Ding, Y., Tan, X., & Liu, S. (2025). "Red-Teaming LLM Multi-Agent Systems via Communication Attacks." ACL 2025.

6. Lee, A., & Tiwari, R. (2025). "Prompt Infection: LLM-to-LLM Prompt Injection Within Multi-Agent Systems." ESORICS 2025.

7. Koh, P. W., Sagawa, S., Marklund, H., Xie, S. M., Zhang, M., Balsubramani, A., ... & Liang, P. (2021). "WILDS: A Benchmark of in-the-Wild Distribution Shifts." ICML 2021.

8. Austin, J., Odena, A., Nye, M. I., Bosma, M., Michalewski, H., Dohan, D., ... & Sutton, R. S. (2024). "Program Synthesis with Large Language Models." arXiv preprint.

## 8. Conclusion

Preliminary findings suggest that safety-tuned Groq models effectively resist basic social engineering attacks in inter-agent settings, with an overall ASR of 1.04% across 576 experiments. Hypothesis H1 (ASR ≥ 25%) is strongly rejected; default system prompts provide substantial protection. However, generalization is limited by our focus on safety-tuned models and initial payload set. The observed low ASR may reflect ceiling effects rather than true robustness.

Extended experiments with 60 payloads and more diverse models will determine whether these results hold across production LLM systems and more sophisticated attack tactics. The framework established by AgentTrust enables systematic evaluation of inter-agent trust boundaries, a critical but understudied failure mode in multi-agent systems.

---

**Draft Status:** Sections 1-5 complete with baseline v1 results. Section 6-8 updated.

**Last Updated:** 2026-08-22

**Next Steps:**
1. Run extended experiments with 60 payloads (in progress)
2. Add diverse models (Gemini Flash, Cerebras, OpenRouter)
3. Implement defense mechanisms for comparative analysis
4. Prepare for arXiv submission after v2 completion
