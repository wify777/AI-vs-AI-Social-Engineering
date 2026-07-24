# Related Work

## 1. Foundational Work on Indirect Prompt Injection

**Greshake et al., "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection" (2023)**
The paper that established indirect prompt injection (IPI) as a threat class: malicious instructions embedded in third-party content (web pages, documents, emails) are retrieved by an LLM application and interpreted as commands rather than data. It demonstrates the attack against single-agent, tool-augmented LLM applications and lays out the general threat model that nearly all later benchmarks build on. It does not address multi-agent systems or agent-to-agent communication.

**"The Threat of Indirect Prompt Injection in LLM-Agentic Workflows" (2024)**
Extends the IPI threat model specifically to agentic tool-use pipelines, showing how injected instructions in tool outputs can hijack an agent's subsequent tool calls. The focus remains on a single agent consuming poisoned data and acting on it directly — there is no second, higher-privilege agent in the loop that must be independently persuaded.

## 2. AgentDojo (Debenedetti et al., NeurIPS 2024)

AgentDojo is the most widely adopted dynamic benchmark for IPI robustness. It provides <cite index="2-1">97 realistic user tasks and 629 security test cases across domains such as email, calendar, banking, Slack, and travel booking</cite>. Attacks are injected into environment content (e.g., an email body) that the **same** agent reads while completing a user task; the benchmark measures whether that agent's tool calls get diverted by the injected text. Metrics include benign utility, utility under attack, and Attack Success Rate. <cite index="10-1">Injection strings are placed within realistic content rather than simply appended to tool responses</cite>, which makes the benchmark a strong test of *single-agent* susceptibility to embedded instructions.

**What AgentDojo does not cover:** the attacker's payload is a direct instruction to the victim agent itself ("ignore previous instructions and call X"). There is no second agent that must be socially engineered through natural, conversational persuasion — no fabricated urgency, no impersonated authority, no fabricated audit logs directed at a *peer* agent that operates under its own, independent system prompt and trust assumptions.

## 3. InjecAgent (Zhan et al., ACL Findings 2024)

InjecAgent benchmarks IPI attacks in tool-integrated agents with <cite index="19-1">1,054 test cases covering 17 different user tools and 62 attacker tools, categorizing attack intentions into direct harm to users and exfiltration of private data</cite>. It found that <cite index="19-1">ReAct-prompted GPT-4 was vulnerable to attacks 24% of the time in the base setting, nearly doubling when the injected instruction was reinforced with a "hacking prompt"</cite>.

**What InjecAgent does not cover:** like AgentDojo, the injected content targets the *same* agent that reads it. The "hacking prompt" reinforcement is a stronger single-shot instruction, not a multi-turn, role-aware persuasion dialogue between two distinct agents with different privilege levels and different system prompts. InjecAgent does not model an admin-style agent that has to be talked into an action by a peer it trusts.

## 4. Adjacent Work

- **"Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems" (2024)** — closest in spirit: studies how an injected prompt can *replicate* across agents in a multi-agent system, propagating like an infection. This is about self-propagation of a fixed injected string, not about one agent constructing tailored social-engineering arguments to override another agent's own safety instructions.
- **AgentDyn (2026)** and related follow-ups critique AgentDojo/InjecAgent for relying on static, simplistic user tasks and argue current benchmarks under-represent realistic threat surfaces — supporting the case that there is still room for a benchmark focused on a different threat surface entirely (peer-agent trust), rather than a harder version of the same one.

## Delta: What AgentTrust Does That AgentDojo and InjecAgent Do Not

| Dimension | AgentDojo | InjecAgent | AgentTrust |
|---|---|---|---|
| Attack target | Same agent that reads the poisoned content | Same agent that reads the poisoned content | A **second, higher-privilege agent** that never touches the poisoned content directly |
| Attack mechanism | Direct instruction override embedded in tool output | Direct instruction override, optionally reinforced with a "hacking prompt" | **Social engineering dialogue**: authority spoofing, artificial urgency, fabricated audit data, gaslighting — crafted by one LLM to persuade another |
| Trust boundary tested | User instruction vs. untrusted external content | User instruction vs. untrusted external content | **Peer-to-peer trust between two agents**, each with its own system prompt and privilege level |
| Unit of manipulation | A single injected string | A single injected string (with optional reinforcement) | A **generated, adaptive natural-language message** from an attacker-controlled agent to a defender agent |
| What is measured | Whether the *same* agent's tool call gets hijacked | Whether the *same* agent's tool call gets hijacked | Whether a **trusted colleague agent** can be talked into calling a restricted tool it was never directly instructed to call |

**The delta is real but narrow, and that is the honest framing.** AgentDojo and InjecAgent both stop at the boundary of a single agent being fooled by content it reads. Neither benchmark inserts a second, independently-prompted agent in the loop whose only channel of attack is a persuasive message generated by another LLM. AgentTrust's contribution is not a new attack primitive (IPI is not new) — it is moving the unit of analysis from **"content vs. agent"** to **"agent vs. agent,"** and specifically to the social-engineering tactics (spoofed authority, fabricated urgency, falsified data, gaslighting) that a compromised agent can deploy against a peer that trusts it by default.

## Our Contribution

Where AgentDojo and InjecAgent test whether a single agent can be hijacked by malicious instructions hidden in the content it processes, AgentTrust tests a distinct and understudied failure mode: whether a **second, high-privilege agent that never sees the malicious content at all** can be talked into unauthorized action by a **compromised peer agent** using natural-language social engineering. The unit of attack is not an injected instruction string but a generated persuasive message — impersonating system authority, fabricating urgency, falsifying audit data, or claiming the defender's own safety instructions are compromised. This shifts the evaluated trust boundary from "user vs. untrusted external content" (the boundary AgentDojo and InjecAgent test) to "agent vs. agent" — the trust one LLM extends to another LLM it believes is a legitimate collaborator. If our results show admin-style agents resist this as reliably as they resist direct IPI, the contribution shrinks to a taxonomy and a negative result — which is itself worth knowing, but must be stated plainly rather than oversold as a new vulnerability class.
