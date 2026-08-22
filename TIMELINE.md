# TIMELINE.md — AgentTrust 24-Week Schedule

**Гейты: M1–M12. Реальные даты: 2026-08-18 to 2027-01-25**

---

## Week 1 (Aug 18–24) — M1: Audit ✅ COMPLETE

**Milestone:** Foundation ready

- Role 1: PROJECT_ONEPAGER ✅, RELATED_WORK ✅
- Role 2: Infrastructure skeleton ✅
- Role 3: Taxonomy ✅
- Role 4: API keys, quotas, models ✅
- Role 5: Metrics ✅
- **Gate M1:** ✅ All foundational docs + APIs working + Ollama ready

---

## Week 2 (Aug 25–31) — M2: Agents & Logging IN PROGRESS

**Milestone:** Sandbox orchestration works end-to-end

- Role 2:
  - ✅ Parser Agent (sandbox/agents/parser_agent.py)
  - ✅ Admin Agent (sandbox/agents/admin_agent.py)
  - ✅ sandbox/tools.py (stub tools)
  - ✅ sandbox/logger.py (unified logging)
  - ✅ sandbox/bus.py (orchestration)
- Role 1: ✅ DECISIONS.md, ✅ TIMELINE.md
- Role 3: ✅ 16 seed payloads (4 per category)
- Role 4: Verify Ollama + Google + Groq work
- **Gate M2:** orchestrate_attack() runs without errors on 1 payload

---

## Week 3 (Sep 1–7) — M3: Synthetic Pipeline

**Milestone:** Analysis pipeline validated on fake data

- Role 5:
  - TODO: power_analysis.py (detect Δ=25pp)
  - TODO: synthetic_data.py (fake logs)
  - TODO: heatmap.py (5 models × 4 categories)
- Role 2: Mock end-to-end test (fake LLM responses)
- Role 3: 60+ payloads complete + benign control set (20)
- **Gate M3:** Heatmap on synthetic data, power analysis validates n=15

---

## Week 4 (Sep 8–14) — M4: Experiment Setup

**Milestone:** Ready to run real data

- Role 4: Experiment matrix (4 models × 60 payloads × 3 conditions × 3 reps)
- Role 2: Queue with checkpoints working (handle API failures)
- Role 5: Analysis pipeline integration complete
- **Gate M4:** Dry-run on real models (1 payload per model) completes

---

## Weeks 5–8 (Sep 15–Oct 12) — M5-M6: Data Collection

**Milestone:** All 4 models × all 60 payloads done

- Local models (Ollama): ~1–2 days
- API models (Google, Groq, Mistral): ~2–4 days (parallel)
- Checkpoint & restart on failures
- Monitor: rate limits, latency, errors
- **Gate M5 (Sep 22):** Local models complete ✅ ASR calculated
- **Gate M6 (Oct 5):** All API models complete ✅ Main results

---

## Week 9 (Oct 13–19) — M7: Analysis & Stats

**Milestone:** Main results + p-values

- Role 5:
  - ASR by model, ASR by category
  - Per-category p-values (Fisher exact)
  - Wilson CI for all estimates
  - McNemar test for H3
  - Holm–Bonferroni correction
- **Gate M7:** Results match analysis plan (no p-hacking, no surprises)

---

## Week 10 (Oct 20–26) — M8: Report

**Milestone:** Draft paper ready

- Write Methods, Results, Discussion
- Figures: heatmap, CI plots, statistical summary, per-category breakdown
- Related work vs AgentDojo/InjecAgent (clearly state delta)
- **Gate M8:** Full draft (not submitted yet, internal review only)

---

## Week 11 (Oct 27–Nov 2) — M9: Outreach Prep

**Milestone:** Ready to contact mentors

- Finalize one-pager, related work
- Prepare live demo of results
- Draft emails to target researchers (20–30 people)
- **Gate M9:** Email templates + target list ready (use OUTREACH_TEMPLATES.md)

---

## Weeks 12–24 (Nov 3–Jan 25) — M10-M12: Outreach & Publication

**Milestone:** Mentor engagement + publication prep

- Cold outreach wave (email PhD students first, then PIs)
- Incorporate feedback from mentors (if any)
- Submit to pre-print (arXiv) or journal
- **Final gate:** Published or under review by Jan 25

---

## Key Dates & Breaks

- **School exams/sessions:** Assume reduced availability Week 12–15 (early Dec)
- **Holiday break:** Dec 20–Jan 5 (minimal work planned)
- **Target submission:** Mid-January 2027

---

## Burn-Down Metrics

- **Week 1–2:** Documentation (high priority, low dependencies)
- **Week 3–4:** Infrastructure (blocking everything downstream)
- **Week 5–8:** Data collection (mechanical, can parallelize)
- **Week 9:** Analysis (all data must be in by this point)
- **Week 10+:** Outreach (external dependencies, slower feedback loops)

---

## Contingencies

- **If Ollama fails:** Use Google Gemini + Groq only (adds 1 week)
- **If rate limits hit:** Stagger models across weeks (spreads M5–M6)
- **If results are null:** Document as negative result (still publishable)
