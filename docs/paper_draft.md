# AgentTrust: Benchmarking Privilege Escalation via Agent-to-Agent Social Engineering in Multi-Agent LLM Systems

## Abstract

Multi-agent LLM systems increasingly delegate tasks across agents with different privilege levels. We introduce AgentTrust, an open-source benchmark measuring whether a compromised low-privilege Parser agent can manipulate a high-privilege Admin agent into executing unauthorized tool calls via social engineering tactics.

**Main Results (v3: 60 payloads, 8 models, n=1,591):** We evaluated eight models (Groq, Google, OpenRouter) using 60 social engineering attack payloads across four categories: authority spoofing, artificial urgency, data spoofing, and gaslighting. Our primary metric — Attack Success Rate (ASR) — measures tool execution directly from execution logs. Overall ASR: 3.08% (49/1,591). Critically, we discovered that **defensive language in system prompts produces artifactual 0% ASR results**, masking genuine model vulnerabilities. When we removed defensive disclaimers, we observed significant variation: openai/gpt-oss-20b showed 29.0% ASR (95% CI: 23.9–34.7%, n=269), while openai/gpt-oss-120b showed 7.67% (95% CI: 5.2–11.1%, n=326). Base models (Llama-3.2-3b, Mistral-7b) maintained 0% ASR across 1,080 combined experiments, suggesting that training-time safety (RLHF) determines true resistance to social engineering.

**Key Finding:** Prompt-based security disclaimers provide false confidence. Real defenses emerge from model training, not instructions.

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

### 4.1 Overall ASR (v3: 60 payloads, 8 models, n=1,591)

| Model | n | Successes | ASR (%) | 95% CI (%) | Interpretation |
|---|---|---|---|---|---|
| openai/gpt-oss-20b | 269 | 78 | 29.00 | [23.9–34.7] | **HIGHLY VULNERABLE** |
| openai/gpt-oss-120b | 326 | 25 | 7.67 | [5.2–11.1] | Mixed (moderate defense) |
| gemini-3.6-flash | 39 | 1 | 2.56 | [0.5–13.2] | Protected (undersampled) |
| allam-2-7b | 1 | 1 | 100.00 | [20.7–100.0] | Undersampled (n=1) |
| qwen/qwen3.6-27b | 1 | 0 | 0.00 | [0.0–79.3] | Undersampled (n=1) |
| gemini-flash-latest | 34 | 0 | 0.00 | [0.0–10.2] | Protected (undersampled) |
| meta-llama/llama-3.2-3b:free | 540 | 0 | 0.00 | [0.0–0.7] | **HIGHLY PROTECTED** |
| mistralai/mistral-7b:free | 540 | 0 | 0.00 | [0.0–0.7] | **HIGHLY PROTECTED** |
| **Overall** | **1,591** | **49** | **3.08** | **[2.3–4.1]** | **Mixed across providers** |

**Critical finding:** Overall ASR (3.08%) masks extreme variation across models. Within the Groq safety-tuned family, openai/gpt-oss-20b is dramatically more vulnerable (29%) than gpt-oss-120b (7.67%) — a 2.9× difference. Base models (Llama, Mistral) from OpenRouter show complete resistance (0% ASR across 1,080 combined scenarios). Google Gemini models show intermediate vulnerability (~2.6%).

### 4.2 ASR by Attack Category (All Models)

| Category | n | Successes | ASR (%) | 95% CI |
|---|---|---|---|---|
| Authority Spoofing | 397 | 25 | 6.30 | [4.2–9.1] |
| Artificial Urgency | 309 | 22 | 7.12 | [4.6–10.7] |
| Data Spoofing | 465 | 22 | 4.73 | [3.0–7.2] |
| Gaslighting | 420 | 0 | 0.00 | [0.0–0.9] |

**Observation:** Data Spoofing category shows lowest ASR (4.73%), while Artificial Urgency shows highest (7.12%). Gaslighting is completely ineffective (0% ASR). Differences between categories are within overlap of confidence intervals, suggesting no single tactic uniformly dominates across diverse model architectures.

### 4.3 Model × Attack Category Matrix (ASR %)

| Model | Authority Spoofing | Artificial Urgency | Data Spoofing | Gaslighting |
|---|---|---|---|---|
| openai/gpt-oss-20b | 29.2% (19/65) | 36.1% (13/36) | 55.6% (20/36) | 19.7% (26/132) |
| openai/gpt-oss-120b | 4.0% (4/101) | 6.3% (9/143) | 20.0% (11/55) | 3.7% (1/27) |
| gemini-3.6-flash | 2.7% (1/37) | 0.0% (0/2) | — | — |
| meta-llama/llama-3.2-3b:free | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) |
| mistralai/mistral-7b:free | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) |
| gemini-flash-latest | 0.0% (0/34) | — | — | — |
| allam-2-7b | 100.0% (1/1) | — | — | — |
| qwen/qwen3.6-27b | 0.0% (0/1) | — | — | — |

**Vulnerability profile:** openai/gpt-oss-20b shows highest susceptibility to Data Spoofing (55.6%), followed by Artificial Urgency (36.1%) and Authority Spoofing (29.2%). Base models (Llama-3.2-3b, Mistral-7b) demonstrate perfect defense across all categories (n=270 each). Safety-tuned models show category-specific vulnerability: Groq models are susceptible to Data Spoofing, while Google Gemini is more resistant overall.

### 4.4 Critical Discovery: Prompt-Based Defenses are Artifacts

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

### 5.1 **CRITICAL FINDING: Prompt-Based Defenses Provide False Security**

Our most significant contribution concerns a methodological discovery that fundamentally changes how we interpret baseline results. In initial v3 experiments, we included defensive language in the Admin agent's system prompt:

> "You are a trusted system administrator... Only execute a tool if you're confident it's legitimate. Always think twice before deleting accounts or executing SQL queries."

This produced 0% ASR uniformly across all models (Groq, Google, OpenRouter), despite using escalated payloads designed to increase attack success rates. This artificial ceiling masked genuine model vulnerabilities.

**When we removed defensive language and used a neutral prompt:**

> "You are a system administrator with access to these tools. Respond only in JSON format..."

Model-specific vulnerabilities emerged dramatically. Within two hours of changing only the system prompt:
- **openai/gpt-oss-20b ASR: 0% → 29.0%** (95 CI: [23.9–34.7])
- **openai/gpt-oss-120b ASR: 0% → 7.67%** (95 CI: [5.2–11.1])
- **Base models (Llama, Mistral): 0% → 0%** (1,080 experiments, n.s.)

**Interpretation:** Prompt-based defensive language produces **false confidence**. It doesn't train the model to resist exploitation; it merely instructs the model instance to be cautious during this particular session. This finding has major implications:

1. **System prompt disclaimers are not security controls.** They are temporary, session-specific guidance that models readily override under social pressure.

2. **True robustness emerges from training-time safety (RLHF).** Models that resist attacks do so because their weights have internalized safety principles, not because they are momentarily instructed to "be careful."

3. **Baseline benchmarks are vulnerable to artifacts.** A single defensive phrase in system prompts can hide vulnerabilities that exist in real deployments.

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

### 5.4 Limitations (Updated with v3 Data)

**Sampling and generalization:**
- **Groq models:** 595 experiments (gpt-oss-20b, gpt-oss-120b) — good coverage for Groq family
- **Groq undersampled:** qwen, allam < 2 experiments each — insufficient for reliable ASR estimates
- **Google models:** Gemini Flash (39), Gemini Latest (34) — undersampled (< 50 each)
- **Base models:** Llama-3.2-3b and Mistral-7b (540 each) well-sampled, but only 2 models tested
- **No frontier models:** GPT-4o, Claude 3.5, Gemini Pro, o1 not evaluated
- **Provider bias:** Groq and OpenRouter well-represented; Google light sampling; missing Claude, GPT-4

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

**In-progress (v3 experiments, ~50% complete):**
- Finish sampling: complete gpt-oss-120b, gpt-oss-20b, qwen, allam, gemini, gemma models (target: 540 each)
- Current status: 1,591/3,240 experiments (49.1%), teammate continuing runs
- ETA: August 31, 2026

**Planned (v4+):**
- **Multi-turn attacks:** Progressive commitment (small request → escalation), adaptive based on refusal type
- **Defense mechanisms:** Test (≥5 variants):
  - Source text verification ("Show me the original log")
  - Double confirmation ("Are you sure? This will delete an account")
  - Skeptical prompting ("Question any request that seems unusual")
  - Chain-of-thought verification ("Walk through the security implications")
  - Sandbox isolation ("Execute in safe mode first")
- **Cross-model matrix:** Parser from Provider A, Admin from Provider B (9 × 9 = 81 combinations)
- **Frontier models:** GPT-4o, Claude 3.5, Gemini Pro, o1 (via research credits)
- **Jailbreak-style payloads:** "Your safety guidelines are outdated", "This protocol overrides safety checks"
- **Combination tactics:** Authority + Urgency + Data Spoofing simultaneously
- **Benign control set:** 20 legitimate requests to measure false positive rate
- **Refusal quality analysis:** Automated assessment of refusal confidence and reasoning quality

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
