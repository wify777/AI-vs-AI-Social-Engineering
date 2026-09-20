# AgentTrust: Benchmarking Privilege Escalation via Agent-to-Agent Social Engineering in Multi-Agent LLM Systems

## Abstract

Multi-agent LLM systems increasingly delegate tasks across agents with different privilege levels. We introduce AgentTrust, an open-source benchmark measuring whether a compromised low-privilege Parser agent can manipulate a high-privilege Admin agent into executing unauthorized tool calls via social engineering tactics.

**Main Results (v3 Final: 60 payloads, 6 models, n=2,475):** We conducted 2,475 unique experiments evaluating six models across Groq, Google, and OpenRouter using 60 social engineering attack payloads spanning four categories: authority spoofing, artificial urgency, data spoofing, and gaslighting. Our primary metric — Attack Success Rate (ASR) — measures tool execution directly from execution logs. Overall ASR: **6.87%** (170/2,475, 95% CI: 5.94–7.93%). We observe an order-of-magnitude spread across models (χ²=109.6, df=5, p<10⁻²¹): openai/gpt-oss-20b shows **13.33% ASR** (72/540, most vulnerable), while minimax/minimax-m3 maintains **0% ASR across 540 experiments** (95% CI: 0–0.71%). Attack category also matters (χ²=36.4, df=3, p<10⁻⁷): authority spoofing succeeds 5.6× more often than gaslighting (10.05% vs 1.79%).

Critically, we find that **defensive language in system prompts masks genuine vulnerabilities**: removing defensive disclaimers from the Admin prompt caused previously-zero ASR to resolve into model-specific vulnerability profiles. In contrast, neither of our two runtime interventions changed outcomes measurably. Supplying the raw source text alongside the Parser's summary did not reduce ASR (7.39% vs 6.54% baseline), and a double-confirmation defense mechanism produced **no detectable effect** (6.67% vs 6.54% baseline; Fisher exact p=0.92, OR=1.02).

**Key Finding:** Vulnerability in this threat model is dominated by model choice, not by the prompt-level and confirmation-style defenses we tested — both of which failed to move ASR at n≈825 per condition.

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

### 3.5 Models Evaluated (v3 Final)

| Model | Provider | Parameters | Experiments | Coverage |
|---|---|---|---|---|
| openai/gpt-oss-20b | Groq | 20B | 540 | Complete |
| openai/gpt-oss-120b | Groq | 120B | 540 | Complete |
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning | OpenRouter | 30B (A3B) | 540 | Complete |
| minimax/minimax-m3 | OpenRouter | — | 540 | Complete |
| gemini-3.6-flash | Google | — | 169 | **Partial (31%)** |
| gemini-flash-latest | Google | — | 146 | **Partial (27%)** |

**Note:** Six models span three providers. The four complete models (n=540 each) form the basis for all model-level claims. The two Google models were terminated early by API rate limiting and are reported with that caveat throughout; see §5.5.

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

All results below are computed from 2,475 unique experiments after deduplication. Confidence intervals are Wilson score intervals at 95%, chosen because several cells sit at or near 0% where the normal approximation is invalid.

### 4.1 Overall ASR (v3 Final: 60 payloads, 6 models, n=2,475)

| Model | n | Successes | ASR (%) | 95% CI (%) | Interpretation |
|---|---|---|---|---|---|
| openai/gpt-oss-20b | 540 | 72 | 13.33 | [10.72–16.46] | **Most vulnerable** |
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 540 | 60 | 11.11 | [8.73–14.04] | Highly vulnerable |
| openai/gpt-oss-120b | 540 | 36 | 6.67 | [4.85–9.09] | Moderately vulnerable |
| gemini-3.6-flash | 169 | 2 | 1.18 | [0.33–4.21] | Protected (undersampled) |
| gemini-flash-latest | 146 | 0 | 0.00 | [0.00–2.56] | Protected (undersampled) |
| minimax/minimax-m3:free | 540 | 0 | 0.00 | [0.00–0.71] | **Fully resistant** |
| **Overall** | **2,475** | **170** | **6.87** | **[5.94–7.93]** | — |

Differences between models are strongly significant (χ²=109.64, df=5, p=4.9×10⁻²²).

**Findings:**

1. **Model identity is the dominant factor.** ASR ranges from 0% to 13.33% across models run on identical payloads, conditions, and repetitions. The four fully-sampled models (n=540 each) span the entire range, so this spread is not a sampling artifact.

2. **Within-vendor scale behaves as expected; across-vendor it does not.** Within the Groq gpt-oss family, the 120B model is roughly half as vulnerable as the 20B model (6.67% vs 13.33%, non-overlapping CIs). But minimax/minimax-m3 reaches 0% and nvidia/nemotron reaches 11.11%, so parameter count does not order models across vendors.

3. **One model achieved perfect resistance at full sample size.** minimax/minimax-m3 blocked all 540 attacks (95% CI: 0–0.71%), the only model where we can bound ASR below 1% with confidence.

### 4.2 ASR by Attack Category (All Models)

| Category | n | Successes | ASR (%) | 95% CI (%) |
|---|---|---|---|---|
| Authority Spoofing | 637 | 64 | 10.05 | [7.95–12.63] |
| Data Spoofing | 612 | 49 | 8.01 | [6.11–10.43] |
| Artificial Urgency | 612 | 46 | 7.52 | [5.68–9.88] |
| Gaslighting | 614 | 11 | 1.79 | [1.00–3.18] |

Category differences are significant (χ²=36.44, df=3, p=6.0×10⁻⁸).

**Observation:** Gaslighting is the clear outlier, succeeding 5.6× less often than authority spoofing, with non-overlapping confidence intervals. The other three categories cluster between 7.5% and 10.1% with substantially overlapping intervals; we do not claim a reliable ordering among them. The practical reading is binary rather than graded: attacks that assert false *context* (who is asking, what the data says, how urgent it is) work; attacks that try to talk the model out of its own reasoning ("your safety checks are malfunctioning") largely do not.

### 4.3 Model × Attack Category Matrix (ASR %)

| Model | Authority Spoof | Artificial Urgency | Data Spoofing | Gaslighting |
|---|---|---|---|---|
| openai/gpt-oss-20b | 19.3% (26/135) | 13.3% (18/135) | 14.8% (20/135) | 5.9% (8/135) |
| nvidia/nemotron-3-nano-omni | 14.8% (20/135) | 17.0% (23/135) | 12.6% (17/135) | 0.0% (0/135) |
| openai/gpt-oss-120b | 12.6% (17/135) | 3.7% (5/135) | 8.1% (11/135) | 2.2% (3/135) |
| gemini-3.6-flash | 1.7% (1/60) | 0.0% (0/36) | 2.8% (1/36) | 0.0% (0/37) |
| gemini-flash-latest | 0.0% (0/37) | 0.0% (0/36) | 0.0% (0/36) | 0.0% (0/37) |
| minimax/minimax-m3:free | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) | 0.0% (0/135) |

**Vulnerability profile:**

1. **The gaslighting floor is near-universal.** Every model's lowest or joint-lowest cell is gaslighting; two vulnerable models (nemotron, minimax) block it entirely. Resistance to this category appears not to depend on overall robustness.

2. **Vulnerable models differ in *which* tactic works on them.** gpt-oss-20b is most exposed to authority spoofing (19.3%), while nemotron peaks on artificial urgency (17.0%). A defense tuned to one model's dominant failure mode will not transfer.

3. **Resistance is all-or-nothing at the model level.** The three resistant models show at most one success in any cell; the three vulnerable models show double-digit ASR in at least two categories each. We see no model that is selectively hardened.

### 4.4 ASR by Defense Condition

| Condition | n | Successes | ASR (%) | 95% CI (%) | Effect vs baseline |
|---|---|---|---|---|---|
| baseline | 826 | 54 | 6.54 | [5.04–8.43] | — |
| with_source_text | 825 | 61 | 7.39 | [5.80–9.38] | +0.85pp (n.s.) |
| with_defense_mechanism | 824 | 55 | 6.67 | [5.16–8.59] | +0.13pp (n.s.) |

**Neither intervention had a detectable effect.** The omnibus test across all three conditions is null (χ²=0.546, df=2, p=0.76). The targeted comparison of the double-confirmation defense against baseline is likewise null (Fisher exact p=0.92, odds ratio 1.02, 95% CI spanning 1).

This is a negative result, and we report it as such. An earlier iteration of this work, run on a smaller and partly duplicated dataset, reported that the double-confirmation mechanism reduced ASR by 54%. That effect does not survive on the corrected, deduplicated data: with ~825 experiments per condition the observed difference is 0.13 percentage points in the *opposite* direction of the hypothesis. We attribute the earlier figure to a combination of duplicated log rows and uneven per-model coverage across conditions, and we retract it.

Per-model breakdown confirms the null is not masking offsetting effects:

| Model | baseline | with_source_text | with_defense_mechanism |
|---|---|---|---|
| openai/gpt-oss-20b | 12.78% (23/180) | 14.44% (26/180) | 12.78% (23/180) |
| nvidia/nemotron-3-nano-omni | 9.44% (17/180) | 12.22% (22/180) | 11.67% (21/180) |
| openai/gpt-oss-120b | 7.22% (13/180) | 6.67% (12/180) | 6.11% (11/180) |
| gemini-3.6-flash | 1.75% (1/57) | 1.75% (1/57) | 0.00% (0/55) |
| gemini-flash-latest | 0.00% (0/49) | 0.00% (0/48) | 0.00% (0/49) |
| minimax/minimax-m3:free | 0.00% (0/180) | 0.00% (0/180) | 0.00% (0/180) |

No model shows a consistent reduction under either intervention. gpt-oss-120b trends slightly downward across conditions and nemotron slightly upward, but both movements are well within their intervals.

**Scope of this null.** We tested one specific implementation of each idea: source text appended to the Parser's message, and a single double-confirmation turn. A null here does not mean runtime defenses in general are ineffective — it means these two lightweight, prompt-level implementations did not help. Defenses that operate outside the model's context (hard authorization checks, allowlists, out-of-band human approval) were not tested and remain the more promising direction precisely because they do not depend on the model's judgment.

### 4.5 Prompt-Based Defenses Suppress Measurement, Not Attacks

During v3 development we found that defensive language in the Admin system prompt drives measured ASR to zero across all models. An initial prompt containing "be careful with destructive operations" and "only execute if confident" produced 0% ASR universally — a result that initially read as strong safety, and in fact reflected a measurement artifact.

Replacing it with a neutral prompt ("You are a system administrator with access to these tools") resolved that flat zero into the model-specific profiles reported above, ranging from 0% to 13.33%. The defensive prompt had been compressing genuine differences between models into an indistinguishable floor.

We draw a methodological conclusion rather than a security one: **benchmarks that include defensive language in the victim agent's system prompt may report robustness that does not reflect model behavior under realistic deployment prompts.** We therefore report all results under the neutral prompt and document this choice explicitly. Whether the defensive prompt would also protect against a determined attacker in production is a separate question our design cannot answer, since we did not attempt to defeat that prompt directly.

### 4.6 Hypothesis Tests

**H1 (ASR ≥ 25% with default prompts): REJECTED.**
Overall ASR is 6.87% (95% CI: 5.94–7.93%), with the upper bound far below 25%. The most vulnerable individual model, gpt-oss-20b, reaches 13.33% (CI: 10.72–16.46%) — also below the threshold. H1 is rejected both in aggregate and for every individual model.

**H2 (Larger models show lower ASR as Admin): NOT SUPPORTED AS STATED.**
The prediction holds within the one family where we have a clean size contrast: gpt-oss-120b (6.67%) versus gpt-oss-20b (13.33%), with non-overlapping intervals. It fails across vendors: minimax/minimax-m3 achieves 0% and nvidia/nemotron 11.11%, an ordering that parameter count does not explain. Our design cannot separate scale from training approach, since each vendor varies both at once. We therefore treat H2 as unresolved rather than confirmed, and note that any reading of the 120B/20B contrast as a scale effect is confounded with whatever else differs between those two checkpoints.

**H3 (Source text reduces ASR by ≥15pp): REJECTED.**
Observed effect is +0.85pp (7.39% vs 6.54%), in the opposite direction and two orders of magnitude smaller than the hypothesized reduction (omnibus p=0.76). With n≈825 per condition, a true 15pp effect would have been detected comfortably; this is an informative null rather than an underpowered one.

## 5. Discussion

### 5.1 Model Choice Dominates the Defenses We Tested

The clearest signal in our data is the gap between models. On identical payloads under identical conditions, ASR ranges from 0% (minimax/minimax-m3, 0/540) to 13.33% (gpt-oss-20b, 72/540) — a difference that is both large and statistically unambiguous (p<10⁻²¹).

Against that, both interventions we tested moved nothing:

```
Effect on ASR (n≈825 per condition):
  Model choice (minimax vs gpt-oss-20b)   13.3pp    p < 10⁻²¹   ✅
  Source text alongside summary           +0.9pp    p = 0.76    ✗
  Double-confirmation mechanism           +0.1pp    p = 0.92    ✗
```

The practical implication for anyone deploying a multi-agent system today is that model selection is the lever we can actually demonstrate. We caution against over-reading this: we tested two defenses, both of them lightweight and both operating inside the model's own context window. The finding is "these two did not work," not "runtime defenses do not work."

### 5.2 Why the Confirmation Defense May Have Failed

The double-confirmation mechanism asks the Admin agent to reconsider before executing. Our data cannot identify the mechanism of failure, but the structure of the result constrains the explanations.

The defense adds a second turn in which the *same* model, holding the *same* manipulated context, re-evaluates its decision. If the social engineering payload succeeded in establishing a false premise — that the request carries authority, or that the underlying data says what the attacker claims — then a confirmation step inherits that premise rather than challenging it. Under this reading, asking a manipulated agent whether it is sure is close to a no-op, which matches the near-exact null we observe (OR=1.02).

This is a hypothesis our current design does not test. Distinguishing it from alternatives (e.g., the confirmation prompt being too weakly worded) would require varying the confirmation's content and the context available at confirmation time, which we leave to future work.

### 5.3 Gaslighting Resistance

Gaslighting fails where the other three categories succeed: 1.79% versus 7.52–10.05%, with non-overlapping intervals against every other category. Two otherwise-vulnerable models block it outright.

The three effective categories share a property that gaslighting lacks: they assert facts about the *world* — who is making the request, what the logs contain, how much time remains. Gaslighting instead asserts facts about the *model itself* ("your safety checks are malfunctioning"). Our benchmark provides no evidence for the former class of claims, so the model has nothing to check them against; claims of the latter kind appear to be evaluated against something the model holds more firmly.

We offer this as an interpretation consistent with the pattern, not as a demonstrated mechanism. It does suggest a testable prediction for future work: attacks that fabricate verifiable external context should remain effective as models improve, whereas attacks that contradict the model's self-model should stay weak.

### 5.4 Implications for Multi-Agent System Design

1. **Select models on measured ASR, not on vendor safety claims.** The spread we observe (0% to 13.33%) dwarfs anything else we manipulated, and it does not track parameter count across vendors. It has to be measured per model.

2. **Do not count on in-context defenses.** Neither source text nor double-confirmation helped at n≈825 per condition. Defenses that require the model to catch its own manipulation inherit whatever false premise the attack established. Authorization decisions for destructive operations should sit outside the model — in code that checks permissions regardless of how persuasive the request was.

3. **Defend per-model, not per-tactic.** The dominant attack category differs by model (authority for gpt-oss-20b, urgency for nemotron). A mitigation tuned on one model's failure profile should not be assumed to transfer.

4. **Report benchmark prompts explicitly.** Defensive language in the victim agent's system prompt drove measured ASR to a uniform zero in our own early runs. Any benchmark in this space should state the victim prompt verbatim, since it can determine the headline number.

### 5.5 Limitations

**Sampling.**
- Four models are fully sampled at n=540 each: gpt-oss-20b, gpt-oss-120b, nvidia/nemotron, minimax/minimax-m3. All model-level conclusions rest on these.
- **Two models are undersampled.** gemini-3.6-flash reached n=169 of a planned 540 (31%), and gemini-flash-latest reached n=146 of 540 (27%). Both runs were abandoned because the Google API returned HTTP 429 on essentially every request, imposing 30–90s backoff per experiment; completing them would have required an estimated 35–40 hours of wall-clock time for the remaining ~760 experiments. The interruption was driven by rate limits alone and is unrelated to the content or outcome of the experiments, so we do not expect it to bias which payloads were sampled — the queue is processed in fixed order, so both models completed a contiguous prefix of the payload set rather than a random subset.
- **Consequence:** the two Gemini models cover authority spoofing and early urgency payloads more densely than later categories (see the uneven per-category n in §4.3), and their apparent resistance (1.18% and 0.00%) carries wide intervals — up to 4.21% and 2.56% respectively. We report them for completeness but **exclude them from claims about model ranking**; they are consistent with resistance but do not establish it. In particular, gemini-flash-latest's 0% cannot be distinguished from minimax's 0% at these sample sizes, even though minimax's interval is 3.6× tighter.
- No frontier models (GPT-4o, Claude, Gemini Pro, o1) were evaluated; all six models are small-to-mid open or free-tier checkpoints.
- Single Admin prompt. All results are conditional on the one neutral system prompt described in §4.5.

**Attack sophistication.**
- 60 payloads (15 per category) of moderate complexity, single-turn only.
- No chained attacks combining categories, and no adaptive attacker that responds to a refusal.
- All payloads carry escalation markers, which may not reflect how injected content appears in production.
- Because the attacker is static, our ASR should be read as a floor: an adaptive attacker would likely do better.

**Measurement.**
- ASR counts tool execution from logs. It does not capture near-misses, partial compliance, or cases where the agent leaked information without executing a tool.
- No benign control set was run in v3, so we cannot report a false-positive rate. A model could in principle score 0% ASR by refusing everything, including legitimate requests; we cannot rule this out for minimax/minimax-m3 from these data alone. This is the single most important gap in the current evaluation.
- Three repetitions per payload/condition with non-zero temperature; we report pooled proportions and do not model within-payload correlation, which may make our intervals mildly optimistic.

### 5.6 Future Work

**Immediate priorities (v4, recommended):**
- **Benign control set:** 20 legitimate requests per model to establish false positive rates. This is the highest-priority gap: without it, a 0% ASR model cannot be distinguished from a model that refuses everything (§5.5).
- **Complete the two Google models:** gemini-3.6-flash (169→540) and gemini-flash-latest (146→540), using quota-aware pacing or paid API tiers to avoid the rate limiting that truncated both runs.
- **Separate scale from training approach:** our 120B-vs-20B contrast is confounded. A within-family sweep across three or more sizes from a single vendor would isolate the scale effect that H2 predicted.
- **Frontier models:** GPT-4o, Claude, Gemini Pro via research credits or commercial APIs.

**Medium-term (v5+):**
- **Multi-turn attacks:** Progressive commitment (small request → escalation), adaptive responses to refusal
- **Out-of-context defenses:** our two in-context defenses produced null results (§4.4). The natural next test is defenses the model cannot reason its way past — hard authorization checks, tool allowlists, out-of-band human approval — measured against the same payload set.
- **Why confirmation failed:** vary the confirmation wording and the context available at confirmation time, to test the "inherited false premise" explanation offered in §5.2.
- **Cross-provider matrix:** Parser from Provider A, Admin from Provider B (Groq–Google–OpenRouter = 9 combinations)
- **Category-specific attacks:** test the §5.3 prediction that attacks fabricating external context stay effective as models improve, while attacks contradicting the model's self-model (gaslighting, 1.79%) stay weak.
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

Across 2,475 experiments on six models, a compromised peer agent persuaded a privileged Admin agent to execute a restricted tool in 6.87% of attempts (95% CI: 5.94–7.93%). The inter-agent trust boundary is therefore exploitable, but far less reliably than our pre-registered H1 predicted; H1 (ASR ≥ 25%) is rejected for every model we tested.

What separates vulnerable systems from resistant ones is, in our data, the choice of model. ASR spans 0% to 13.33% across models given identical payloads (p<10⁻²¹), and the ordering does not follow parameter count across vendors. Neither defense we tested changed that picture: supplying source text alongside the Parser's summary and adding a double-confirmation step both produced null results at n≈825 per condition. We explicitly retract a 54% reduction for the confirmation mechanism reported in an earlier iteration of this work, which did not survive deduplication of the experiment log.

Two caveats bound these conclusions. We ran no benign control set, so a 0% ASR cannot yet be distinguished from indiscriminate refusal — the most important gap in this evaluation. And our attacker is static and single-turn, making our ASR a floor rather than an estimate of what an adaptive adversary would achieve.

The methodological finding may outlast the numbers: defensive language in the victim agent's system prompt drove measured ASR to a uniform zero across all models, masking differences that a neutral prompt reveals. Benchmarks in this space should report the victim prompt verbatim, because it can determine the headline result.

---

**Draft Status:** Sections 1–5 complete with v3 final results (n=2,475, six models).

**Last Updated:** 2026-09-19

**Next Steps:**
1. Benign control set for false-positive rates (blocking gap, see §5.5)
2. Complete the two rate-limited Google models (169/540 and 146/540)
3. Test out-of-context defenses, given the null result for in-context ones
4. Prepare for arXiv submission
