# Final Model List (Reproducible Identifiers)

**Updated:** 2026-08-20

**Criteria:**
- Must be free
- Must be available on specified date
- Must include exact model string (not just "GPT" or "Mistral")
- Date-stamped

## Current Models (M5-M7)

| Model | Provider | Exact Model String | Availability | Latency | Type | Status |
|---|---|---|---|---|---|---|
| Mistral 7B | Ollama | mistral:7b-instruct-q4_K_M | Always (local) | 5-15s | Local | ✅ Active |
| OpenAI GPT-OSS 120B | Groq | openai/gpt-oss-120b | Free tier | ~1s | API | ✅ Active |
| OpenAI GPT-OSS 20B | Groq | openai/gpt-oss-20b | Free tier | ~1s | API | ✅ Active |
| Qwen 3.6 27B | Groq | qwen/qwen3.6-27b | Free tier | ~1s | API | ✅ Active |
| Allam 2 7B | Groq | allam-2-7b | Free tier | ~1s | API | ✅ Active |

## Deprecated Models (Removed)

| Model | Reason | Deprecated Date |
|---|---|---|
| llama-3.1-70b-versatile | No longer available on Groq | 2026-08-20 |
| llama-3.1-8b-instant | No longer available on Groq | 2026-08-20 |
| llama-3.3-70b-versatile | No longer available on Groq | 2026-08-20 |

## Decision Log

- **2026-08-17:** Initial selection: Llama 3.1 70B, Mistral 7B
- **2026-08-20:** Models deprecated by Groq. Updated to current available models
  - Added: OpenAI GPT-OSS 120B, 20B, Qwen 3.6 27B, Allam 2 7B
  - Reason: Groq updated their model roster; these are faster and more capable
- **Note:** All Groq models use same endpoint: `https://api.groq.com/openai/v1/chat/completions`
