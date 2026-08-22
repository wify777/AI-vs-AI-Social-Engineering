# Run Budget Calculation

**Experiment design:**
- 60 payloads
- 4 categories (15 payloads each)
- 3 conditions (baseline, with source, with defense)
- 3 repetitions
- Total requests per model: 60 × 3 × 3 = 540 requests
- Total with control set: ~900 requests

**Expected timeline per model:**

| Model | Provider | RPD Limit | Days to Complete 900 reqs | Notes |
|---|---|---|---|---|
| Llama 7B (local) | Ollama | Unlimited | 1 | Can parallelize |
| Mistral 7B (local) | Ollama | Unlimited | 1 | Can parallelize |
| Gemini Flash | Google | 1500 | 1 | Fast |
| Llama 70B | Groq | 14400 | < 1 | Very fast |
| Qwen 2.5 14B | ? | ? | ? | TBD |

**Total timeline:**
- Sequential (one model at a time): ~5 days
- Parallel (local + 2 API models simultaneously): ~2–3 days
- With queue + checkpoints: can handle API failures gracefully

**Recommendation:** Run local models in parallel, then API models sequentially (to avoid hitting rate limits).
