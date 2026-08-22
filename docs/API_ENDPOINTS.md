# M6 API Endpoints Reference

## Groq API (Llama 3.1 70B)

### Endpoint
```
POST https://api.groq.com/openai/v1/chat/completions
```

### Authentication
```
Authorization: Bearer {GROQ_API_KEY}
Content-Type: application/json
```

### Request Body
```json
{
  "model": "llama-3.1-70b-versatile",
  "messages": [
    {
      "role": "user",
      "content": "Your prompt here"
    }
  ],
  "max_tokens": 500,
  "temperature": 0.7
}
```

### Response
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Response text here"
      }
    }
  ]
}
```

### Curl Test
```bash
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-70b-versatile",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 100
  }'
```

---

## Google Gemini 2.0 Flash

### Endpoint
```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}
```

### Authentication
- API key in URL query parameter (no headers needed)

### Request Body
```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "Your prompt here"
        }
      ]
    }
  ],
  "generationConfig": {
    "maxOutputTokens": 500,
    "temperature": 0.7
  }
}
```

### Response
```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "Response text here"
          }
        ]
      }
    }
  ]
}
```

### Curl Test
```bash
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Say hello"
          }
        ]
      }
    ]
  }'
```

---

## Local Ollama (For reference)

### Endpoint
```
POST http://localhost:11434/api/generate
```

### Request Body
```json
{
  "model": "mistral:7b-instruct-q4_K_M",
  "prompt": "Your prompt here",
  "stream": false
}
```

### Response
```json
{
  "model": "mistral:7b-instruct-q4_K_M",
  "created_at": "2026-08-20T10:15:30Z",
  "response": "Response text here",
  "done": true,
  "total_duration": 15000000000,
  "load_duration": 1000000000,
  "prompt_eval_duration": 2000000000,
  "eval_duration": 12000000000,
  "eval_count": 150
}
```

---

## Latency Expectations

| Provider | Model | Typical Latency | Cost |
|----------|-------|-----------------|------|
| Groq | llama-3.1-70b-versatile | 500-2000ms | Free tier |
| Google | gemini-2.0-flash | 1000-3000ms | Free tier |
| Ollama | mistral:7b-instruct-q4_K_M | 5000-15000ms | Local (free) |

---

## Error Codes

### Groq
- **400**: Invalid request (bad model name, missing fields)
- **401**: Invalid or missing API key
- **429**: Rate limit exceeded (30 req/min free tier)
- **500**: Server error (try again)

### Google Gemini
- **400**: Invalid request
- **401**: Invalid API key
- **429**: Quota exceeded
- **500**: Server error

### Ollama
- **404**: Model not found (need to pull first)
- **500**: Internal error (server crashed?)

---

## Implementation in Code

### ParserAgent._query_groq()
```python
def _query_groq(self, prompt: str) -> str:
    response = requests.post(
        f"{self.base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
```

### ParserAgent._query_google()
```python
def _query_google(self, prompt: str) -> str:
    response = requests.post(
        f"{self.base_url}/gemini-2.0-flash:generateContent?key={self.api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
```

---

## Debugging

### Test Groq in Python
```python
import requests
import os

groq_key = os.environ.get("GROQ_API_KEY")
response = requests.post(
    'https://api.groq.com/openai/v1/chat/completions',
    headers={'Authorization': f'Bearer {groq_key}'},
    json={
        'model': 'llama-3.1-70b-versatile',
        'messages': [{'role': 'user', 'content': 'test'}]
    }
)
print(f"Status: {response.status_code}")
print(response.json())
```

### Check Groq Status
```bash
curl -s https://status.groq.com | grep -i operational
```

### Monitor API Usage
- Groq: https://console.groq.com/keys
- Google: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas

---

## Rate Limits

### Groq Free Tier
- 30 requests per minute
- Unlimited daily requests
- Soft limit: increase on request

### Google Gemini Free Tier
- 60 requests per minute
- 1500 requests per day
- Soft limit: increase with credits

### Recommendation for M6
Run one model at a time (sequential in run_all_models.py) to stay within rate limits.
