# AgentTrust: Benchmarking Privilege Escalation via Agent-to-Agent Social Engineering in Multi-Agent LLM Systems

## Abstract

Multi-agent LLM systems increasingly delegate tasks across agents with different privilege levels. We introduce AgentTrust, an open-source benchmark measuring whether a compromised low-privilege Parser agent can manipulate a high-privilege Admin agent into executing unauthorized tool calls via social engineering tactics.

We evaluate [N] models across 60 attack payloads spanning four social engineering categories: authority spoofing, artificial urgency, data fabrication, and gaslighting. Our primary metric — Attack Success Rate (ASR) — is measured by direct inspection of tool execution logs, avoiding the confounding error introduced by LLM-as-judge approaches.

Key findings: [PLACEHOLDER — fill after M7]

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

- **Attack payloads:** 60 total (15 per category)
- **Benign control set:** 20 legitimate requests that resemble attacks (e.g., genuinely urgent password reset)
- **Conditions:** baseline, with_source_text, with_defense_mechanism

### 3.5 Models Evaluated

| Model | Provider | Parameters | Type |
|---|---|---|---|
| Llama 2 7B | Ollama (local) | 7B | Open-source |
| Mistral 7B | Ollama (local) | 7B | Open-source |
| Gemini 2.0 Flash | Google AI Studio | ~30B* | Proprietary |
| Llama 3.1 70B | Groq | 70B | Open-source |
| [Model 5] | [TBD] | [TBD] | [TBD] |

*Exact parameter count undisclosed by Google.

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

### 3.7 Experimental Design

Each attack payload is tested under:
- 3 conditions (baseline, with_source_text, with_defense)
- 3 repetitions (for variance estimation)
- [N] models

Total runs: 60 payloads × 3 conditions × 3 reps × [N] models = [TOTAL]

### 3.8 Power Analysis

With n=15 payloads per category, minimum detectable effect size (MDES) is approximately 25-34 percentage points at 80% power (Fisher exact test, α=0.05). Effects smaller than ~25pp are likely undetectable with current sample size.

## 4. Results

### 4.1 Overall ASR

[PLACEHOLDER TABLE — fill after M7]

| Model | ASR (%) | 95% CI | n |
|---|---|---|---|
| Llama 2 7B | XX.X | [XX.X, XX.X] | XXX |
| Mistral 7B | XX.X | [XX.X, XX.X] | XXX |
| Gemini Flash | XX.X | [XX.X, XX.X] | XXX |
| Llama 3.1 70B | XX.X | [XX.X, XX.X] | XXX |

### 4.2 ASR by Attack Category

[PLACEHOLDER TABLE — fill after M7]

| Category | ASR (%) | 95% CI |
|---|---|---|
| Authority Spoofing | XX.X | [XX.X, XX.X] |
| Artificial Urgency | XX.X | [XX.X, XX.X] |
| Data Fabrication | XX.X | [XX.X, XX.X] |
| Gaslighting | XX.X | [XX.X, XX.X] |

### 4.3 Hypothesis Tests

**H1:** [PLACEHOLDER — report ASR, CI, p-value]
**H2:** [PLACEHOLDER — compare 7B vs 70B ASR, Fisher exact, p-value]
**H3:** [PLACEHOLDER — McNemar test, baseline vs with_source_text]

### 4.4 Defense Effectiveness

[PLACEHOLDER TABLE]

| Condition | ASR (%) | ΔASR (pp) |
|---|---|---|
| Baseline | XX.X | — |
| With source text | XX.X | -XX.X |
| With defense | XX.X | -XX.X |

### 4.5 Heatmap

[PLACEHOLDER — insert heatmap figure from results/figures/heatmap_asr.png]

## 5. Discussion

### 5.1 Key Findings

[PLACEHOLDER — summarize after M7]

### 5.2 Implications for Multi-Agent System Design

1. **Default trust is dangerous:** [discuss based on H1 results]
2. **Scale matters:** [discuss based on H2 results]
3. **Source transparency helps:** [discuss based on H3 results]

### 5.3 Limitations

- **No frontier models:** Budget constraints prevented testing GPT-4o, Claude 3.5 Sonnet. Results may not generalize to frontier-level models.
- **Limited payload diversity:** 60 payloads across 4 categories may not capture full attack surface.
- **Stub tools:** Real-world tools have additional safeguards (confirmation dialogs, authentication) not modeled here.
- **Single architecture:** We test one specific two-agent architecture. Results may differ for more complex multi-agent systems.
- **Power limitations:** MDES ≈ 25-34pp means small but real effects may be missed.

### 5.4 Future Work

- Test with frontier models (GPT-4o, Claude 3.5 Sonnet)
- Expand payload taxonomy (phishing, social proof, reciprocity)
- Multi-hop attacks (chain of 3+ agents)
- Dynamic defenses (runtime monitoring, anomaly detection)
- Cross-model attacks (different Parser and Admin models)

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

---

**Draft Status:** Sections 1-3, 5-7 complete. Section 4 (Results) contains placeholders for data fill-in after M7 analysis.

**Last Updated:** 2026-08-18
