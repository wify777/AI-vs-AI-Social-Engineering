# API Quotas & Limits (as of 2026-08-17)

| Provider | Model | Type | RPM | RPD | TPM | Free Tier | Data Used for Training | Notes |
|---|---|---|---|---|---|---|---|---|
| Google AI Studio | Gemini 2.0 Flash | Free | 60 | 1500 | 1M | ✅ Yes | ❌ No | Fast, new model |
| Groq | Llama-3.1-70B | Free | 30 | 14400 | 6000 | ✅ Yes | ❌ No | Very fast |
| Mistral | Mistral Small | Free | 10 | ? | 500K | ✅ Yes | ❌ No | Check exact limits |
| Cerebras | Llama-3.1-70B | Free | ? | ? | ? | ✅ Yes | ❌ No | Need to verify |
| OpenRouter | Models with :free | Free | Varies | Varies | Varies | ✅ Yes | ❌ No | Check each model |
| Hugging Face | Open models | Free | Unlimited | Unlimited | Unlimited | ✅ Yes | ✅ Yes | Local inference |

**Legend:**
- RPM = Requests Per Minute
- RPD = Requests Per Day
- TPM = Tokens Per Minute
- "Data Used for Training" = does provider train on our queries?

**How to fill this:**
1. For each provider, visit their pricing/limits page
2. Write down ACTUAL limits (not estimates)
3. If limit says "contact sales", write "Unknown"
4. Save file
