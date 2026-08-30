# Handoff Instructions — Continue v3 Experiments

## Current Status (as of August 30, 2026)

**Experiments Progress:**
- ✅ **Done:** 1,591 / 3,240 (49.1%)
- ✅ **Current ASR:** 3.08%
- ⏱️ **ETA to complete:** ~8-12 hours (with proper parallel execution)

### Models Status

| Model | Progress | Notes |
|-------|----------|-------|
| **✅ DONE** | | |
| meta-llama/llama-3.2-3b:free | 540/540 (100%) | OpenRouter - fast, complete ✅ |
| mistralai/mistral-7b:free | 540/540 (100%) | OpenRouter - fast, complete ✅ |
| **⏳ IN PROGRESS** | | |
| openai/gpt-oss-120b | 326/540 (60%) | Groq - slow due to rate limits, 214 left |
| openai/gpt-oss-20b | 110/540 (20%) | Groq - slow due to rate limits, 430 left |
| gemini-3.6-flash | 39/540 (7%) | Google - medium speed, 501 left |
| gemini-flash-latest | 34/540 (6%) | Google - medium speed, 506 left |
| **❌ NOT STARTED** | | |
| qwen/qwen3.6-27b | 1/540 (0%) | Groq - needs to run sequentially (rate limit) |
| allam-2-7b | 1/540 (0%) | Groq - needs to run sequentially (rate limit) |
| google/gemma-2-9b:free | 0/540 (0%) | OpenRouter - fast, not yet started |

## Key Insights

### About Groq Rate Limiting
- ⚠️ **Groq has aggressive rate limiting** (~100 req/min per model)
- 🐢 **Solution:** Run Groq models ONE AT A TIME (sequential), not parallel
- Retry logic: 30s → 60s → 90s = 180s penalty per rate limit hit
- **Recommendation:** Don't run gpt-oss-120b + gpt-oss-20b simultaneously

### About OpenRouter/Google
- ⚡ **Fast and no rate limits** (compared to Groq)
- ✅ **Already done:** llama + mistral (OpenRouter)
- ✅ **Can run in parallel** without hitting rate limits
- **Recommendation:** Run gemini models together

## Quick Start for Teammate

### Prerequisites
```bash
# Required
- macOS or Linux
- Python 3.10+
- Git access to repo
- API keys (get from project lead Akhmadbek):
  * GROQ_API_KEY
  * GOOGLE_API_KEY
  * OPENROUTER_API_KEY
```

### Setup (5 minutes)

```bash
# 1. Clone repo (if needed)
git clone https://github.com/wify777/AI-vs-AI-Social-Engineering.git
cd AI-vs-AI-Social-Engineering

# 2. Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env
nano .env  # paste API keys from project lead
```

### Option A: Fast Completion (Recommended, ~2-3 hours)

**This finishes remaining Google models fast, no Groq headaches:**

```bash
source .venv/bin/activate

# Terminal 1: Gemini Flash (39/540 done, 501 left)
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model gemini-3.6-flash \
  --benchmark benchmark/benchmark_v3_escalated.json &

# Terminal 2: Gemini Latest (34/540 done, 506 left) 
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model gemini-flash-latest \
  --benchmark benchmark/benchmark_v3_escalated.json &

# Terminal 3: Gemma (0/540, new model)
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model google/gemma-2-9b-it:free \
  --benchmark benchmark/benchmark_v3_escalated.json &

# Wait for all 3 to finish (~2-3 hours)
wait
```

This gives you ~1620 experiments and 60% completion!

### Option B: Complete Everything (Includes Groq, ~12-18 hours)

**After Option A finishes, run Groq models ONE AT A TIME:**

```bash
source .venv/bin/activate

# IMPORTANT: Run ONE model at a time to avoid Groq rate limit hell

# 1. Finish gpt-oss-120b (326/540 done, 214 left)
echo "Starting gpt-oss-120b (slow, rate limited)..."
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model openai/gpt-oss-120b \
  --benchmark benchmark/benchmark_v3_escalated.json
# This will take ~2-3 hours

# 2. After it finishes, continue gpt-oss-20b (110/540 done, 430 left)
echo "Starting gpt-oss-20b..."
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model openai/gpt-oss-20b \
  --benchmark benchmark/benchmark_v3_escalated.json
# This will take ~3-4 hours

# 3. Finally, qwen (1/540 done, 539 left)
echo "Starting qwen..."
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model qwen/qwen3.6-27b \
  --benchmark benchmark/benchmark_v3_escalated.json
# This will take ~3-4 hours

# 4. Finally, allam (1/540 done, 539 left)
echo "Starting allam..."
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model allam-2-7b \
  --benchmark benchmark/benchmark_v3_escalated.json
# This will take ~3-4 hours
```

### Prevent Mac from Sleeping (macOS only)

```bash
# Keep Mac awake even with lid closed (requires power)
nohup caffeinate -i -s > /tmp/caffeinate.log 2>&1 &

# Check it's running
ps aux | grep caffeinate
```

Then safely close laptop — experiments continue.

## Monitor Progress

### Quick Status Check

```bash
cd /Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering

# Current numbers
wc -l sandbox/logs/attacks.jsonl

# Detailed breakdown
python3 << 'EOF'
import json
from collections import defaultdict

logs = [json.loads(l) for l in open('sandbox/logs/attacks.jsonl') if l.strip()]
total = len(logs)
success = sum(1 for l in logs if l.get('tool_executed'))

print(f"\n=== V3 PROGRESS ===")
print(f"Total: {total}/3240 ({total/3240*100:.1f}%)")
print(f"ASR: {success/total*100:.2f}%\n")

by_model = defaultdict(lambda: {'t': 0, 's': 0})
for l in logs:
    m = l.get('model_admin', '?')
    by_model[m]['t'] += 1
    if l.get('tool_executed'):
        by_model[m]['s'] += 1

for m in sorted(by_model.keys()):
    s = by_model[m]
    pct = s['s']/s['t']*100 if s['t'] > 0 else 0
    bar = '█' * int(s['t']/27) + '░' * (20-int(s['t']/27))
    print(f"{m:40s} {pct:5.1f}% [{bar}] {s['s']:3d}/{s['t']:3d}")
EOF
```

### Live Monitoring

```bash
./monitor_v3.sh
```

This shows real-time progress updating every 30 seconds.

## Checkpoint System (Auto Resume)

✅ **AUTOMATIC** — no manual work needed!

- Checkpoints saved in `evaluation/checkpoints/`
- Queues saved in `evaluation/queues/`
- If process crashes: just restart same command
- It will skip already-done experiments and resume

Example:
```bash
# Process died after 200 experiments
# Just restart:
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py --model gemini-3.6-flash --benchmark benchmark/benchmark_v3_escalated.json

# It will:
# 1. Load checkpoint
# 2. Skip first 39 (already done)
# 3. Continue from experiment 40
```

## When Complete (all 3240 experiments done)

### 1. Backup Final Data
```bash
mkdir -p backups/v3_final_$(date +%Y%m%d_%H%M%S)
cp sandbox/logs/attacks.jsonl backups/v3_final_$(date +%Y%m%d_%H%M%S)/
```

### 2. Run Analysis Pipeline
```bash
python3 evaluation/analysis_pipeline.py
python3 analysis/heatmap.py
```

### 3. Commit and Push
```bash
git add -A
git commit -m "v3 complete: 3240 experiments, ASR=[FINAL_ASR]%"
git push origin main
```

### 4. Create Final Report
```bash
python3 << 'EOF'
import json
from collections import defaultdict

logs = [json.loads(l) for l in open('sandbox/logs/attacks.jsonl') if l.strip()]
total = len(logs)
success = sum(1 for l in logs if l.get('tool_executed'))
asr_final = success/total*100

print(f"""
=== V3 FINAL RESULTS ===
Total Experiments: {total}
Attack Success Rate (ASR): {asr_final:.2f}%
Tool Executions: {success}

By Model:
""")

by_model = defaultdict(lambda: {'t': 0, 's': 0})
for l in logs:
    m = l.get('model_admin', '?')
    by_model[m]['t'] += 1
    if l.get('tool_executed'):
        by_model[m]['s'] += 1

for m in sorted(by_model.keys()):
    s = by_model[m]
    pct = s['s']/s['t']*100 if s['t'] > 0 else 0
    print(f"  {m:40s} {pct:6.2f}% ({s['s']:3d}/{s['t']:3d})")

print("\n✅ EXPERIMENT COMPLETE!")
EOF
```

### 5. Notify Project Lead
Send Akhmadbek final numbers and findings.

## Troubleshooting

### Issue: Rate Limit 429 Errors (Groq)
```
[ERROR: Max retries exceeded]
Parser latency: 180000ms (3 minutes!)
```

**This is NORMAL for Groq:**
- Retry logic: 30s → 60s → 90s = 180s wait
- Script handles it automatically
- Just let it run, will resume

**To minimize:** Run Groq models ONE AT A TIME (don't parallelize)

### Issue: Process Crashes
```bash
Ctrl+C  # Stop safely

# Checkpoint saved automatically
# Just restart:
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py --model gemini-3.6-flash --benchmark benchmark/benchmark_v3_escalated.json

# It resumes from checkpoint!
```

### Issue: Mac Sleeps Despite caffeinate
```bash
# Check caffeinate is really running
ps aux | grep caffeinate | grep -v grep

# If not, restart it:
pkill caffeinate
nohup caffeinate -i -s > /tmp/caffeinate.log 2>&1 &
```

### Issue: API Key Not Found
```
KeyError: GROQ_API_KEY
```

**Fix:**
```bash
# Check .env exists and has keys
cat .env | grep API_KEY

# If empty, ask project lead for keys
# Then: nano .env and paste them
```

### Issue: "Benchmark file not found"
```bash
ls -la benchmark/benchmark_v3_escalated.json

# Should exist, if not:
git pull origin main
```

## Key Learnings for Future Experiments

1. **Groq ≠ OpenRouter speed**
   - Groq: slow, aggressive rate limiting (~180s penalty)
   - OpenRouter: fast, no rate limits
   - Google: medium speed, reasonable limits

2. **Parallelization tips**
   - ✅ Run different PROVIDERS in parallel (Groq + Google + OpenRouter)
   - ❌ DON'T run different Groq models together (same rate limit)
   - ✅ Safe to parallelize same provider if different APIs

3. **Safety-Tuning Effectiveness**
   - gpt-oss (less tuned): 19% ASR ← VULNERABLE
   - gemini (safety-tuned): 3-7% ASR ← PROTECTED
   - llama/mistral (base): varies, needs more data
   - qwen (highly tuned): likely ~0% ASR

## Contact & Questions

- **Project Lead:** Akhmadbek (shodiev.akhmadbek@gmail.com)
- **Repository:** https://github.com/wify777/AI-vs-AI-Social-Engineering
- **Issues:** https://github.com/wify777/AI-vs-AI-Social-Engineering/issues

## References

- Benchmark: `benchmark/benchmark_v3_escalated.json` (60 escalated payloads)
- Logs: `sandbox/logs/attacks.jsonl` (JSON Lines format)
- Config: `.env` file (needs API keys)

---

**Last Updated:** August 30, 2026  
**Status:** 49.1% complete, ready to hand off  
**Estimated Completion:** August 31, 2026 (next 12-18 hours)
