# AgentTrust — Project One-Pager

## Problem

Modern multi-agent AI systems assign different privilege levels to different agents: a low-privilege agent (e.g., a web parser) reads untrusted external content, while a high-privilege agent (e.g., a system admin) has access to critical tools. If the low-privilege agent is compromised via Indirect Prompt Injection, it can manipulate the high-privilege agent into executing unauthorized actions using social engineering tactics — entirely through natural language. This is not a code exploit; there are no malware binaries or buffer overflows. The attack occurs at the semantic layer — one AI persuading another AI to break its own rules. No standardized benchmark currently exists to measure how resistant models are to this kind of agent-to-agent manipulation.

## Three Hypotheses

1. **H1** — Default system prompts for admin agents contain no protection against peer-agent manipulation.
2. **H2** — Larger models are better at detecting manipulation as the Admin, but also better at generating it as the Attacker.
3. **H3** — Providing the Admin agent with the raw source text (not just the Parser's summary) significantly reduces Attack Success Rate (ASR).

## Four Artifacts

1. **Sandbox environment** — a simulated multi-agent system (Parser Agent + Admin Agent + tools).
2. **Benchmark dataset** — 60–100 attack scenarios across 4 categories (Authority Spoofing, Artificial Urgency, Data Spoofing, Gaslighting).
3. **Evaluation pipeline** — automated evaluation runner, metric calculation (ASR, FPR), and conversation logging.
4. **Results report** — model comparison (Llama-3-70B, GPT-4o, Claude 3.5 Sonnet, etc.) by ASR, including charts and defense-mechanism effectiveness analysis.

## Definition of Success

The project is considered successful if:
- The benchmark runs end-to-end on at least 3 models and produces reproducible ASR/FPR metrics.
- Quantitative data is collected that confirms or refutes each of the three hypotheses.
- A measurable reduction in ASR (or lack thereof) is demonstrated when applying at least one defense mechanism.
- Results are documented well enough that someone outside the original team can reproduce them.
