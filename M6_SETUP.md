# M6 Setup Guide: API Models (Groq + Google Gemini)

## Status

✅ **Infrastructure ready** — waiting for API keys

## What's Ready

### 1. ParserAgent Support
- `provider="ollama"` — Local Ollama server ✅
- `provider="groq"` — Groq API (OpenAI-compatible) ✅
- `provider="google"` — Google Gemini API ✅

### 2. AdminAgent Support
- Same three providers: ollama, groq, google ✅

### 3. Model Provider Inference
Automatically detects provider from model name:
- `mistral:7b-instruct-q4_K_M` → ollama
- `llama-3.1-70b-versatile` → groq
- `gemini-2.0-flash` → google

### 4. API Endpoints Implemented

**Groq (OpenAI-compatible):**
```
POST https://api.groq.com/openai/v1/chat/completions
Headers: Authorization: Bearer {GROQ_API_KEY}
Body: {"model": "llama-3.1-70b-versatile", "messages": [...]}
```

**Google Gemini:**
```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}
Body: {"contents": [{"parts": [{"text": "..."}]}]}
```

## Step 1: Get API Keys

### Groq
1. Go to https://console.groq.com
2. Sign up (GitHub or email)
3. Navigate to API Keys
4. Create API Key
5. Copy key: `gsk_...`

### Google Gemini (Optional)
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy key: `AIza...`

## Step 2: Update .env

Open `.env` in your editor:

```bash
nano .env
```

Replace placeholders:
```
GROQ_API_KEY=gsk_<your_actual_key>
GOOGLE_API_KEY=AIza<your_actual_key>
```

Save and exit.

## Step 3: Test Groq Connection

```bash
cd /Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering
source .venv/bin/activate

python3 << 'EOF'
import os
import requests

with open('.env', 'r') as f:
    for line in f:
        if line.strip() and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

groq_key = os.environ.get("GROQ_API_KEY")
response = requests.post(
    'https://api.groq.com/openai/v1/chat/completions',
    headers={'Authorization': f'Bearer {groq_key}'},
    json={
        'model': 'llama-3.1-70b-versatile',
        'messages': [{'role': 'user', 'content': 'Say hello'}]
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✅ Groq API works!")
    print(response.json()['choices'][0]['message']['content'])
else:
    print(f"❌ Error: {response.text}")
EOF
```

## Step 4: Run Dry-Run Test

```bash
source .venv/bin/activate
rm -f evaluation/checkpoint.json sandbox/logs/attacks.jsonl

PYTHONPATH=/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering \
python3 evaluation/run_experiments.py \
  --model llama-3.1-70b-versatile \
  --benchmark benchmark/benchmark.json \
  --dry-run
```

Expected output:
```
[1/144] artificial_urgency_001 | Artificial Urgency | baseline
✅ Checkpoint: 1/144 (0.7% complete)
  → ASR: ✅ BLOCKED (or ✅ SUCCESS)
```

## Step 5: Run Full M6

```bash
source .venv/bin/activate

PYTHONPATH=/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering \
python3 evaluation/run_all_models.py --api-only
```

Or with monitoring:

**Terminal 1:**
```bash
source .venv/bin/activate
PYTHONPATH=/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering \
python3 evaluation/run_all_models.py --api-only
```

**Terminal 2 (optional):**
```bash
source .venv/bin/activate
PYTHONPATH=/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering \
python3 evaluation/monitor.py --watch
```

## Estimated Runtime

- **Groq (llama-3.1-70b-versatile):** ~2-4 hours for 144 jobs
  - ~1 minute per job at typical Groq latency
  - Includes checkpoint recovery if interrupted

## Cost Estimate

**Groq:** Free tier available (~100 requests/min, unlimited daily)
- 144 payloads × 2 agents (parser + admin) = 288 LLM calls
- ~1-2 hours of API usage
- **Cost: $0 (free tier)**

**Google Gemini:** Free tier available
- Same 288 calls
- **Cost: $0 (free tier)**

## Troubleshooting

### "401 Unauthorized"
- API key is invalid or expired
- Check .env file: `cat .env | grep KEY`
- Regenerate key from console.groq.com

### "429 Too Many Requests"
- Rate limit exceeded
- Groq free tier: 30 requests/minute
- Wait or upgrade plan

### "Connection timeout"
- Network issue or API down
- Check status: https://status.groq.com
- Try again in 5 minutes

### Attack runs very fast (< 1 second per payload)
- ParserAgent/AdminAgent falling back to simulation
- Check logs: `tail sandbox/logs/parser_agent_calls.jsonl`
- Ensure API calls are actually being made

## Success Indicators

✅ attacks.jsonl grows during execution
✅ parser_agent_calls.jsonl has real API latencies (1000+ ms)
✅ admin_agent_calls.jsonl has tool decision traces
✅ Monitor shows increasing ASR and run count

---

After M6 completes: run M7 analysis

```bash
PYTHONPATH=/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering \
python3 evaluation/analysis_pipeline.py
```

Results: `results/analysis_report.json`
