#!/usr/bin/env python3
"""Test Google Gemini and Cerebras APIs"""

import sys
sys.path.insert(0, '/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering')

from dotenv import load_dotenv
import os
import requests

load_dotenv()

print("=" * 80)
print("🧪 TESTING NEW PROVIDERS")
print("=" * 80)

# Test Google Gemini
print("\n1️⃣ GOOGLE GEMINI API")
print("-" * 80)

google_key = os.getenv('GOOGLE_API_KEY')
if not google_key or google_key.startswith('your_'):
    print("⚠️  GOOGLE_API_KEY is placeholder or missing")
    print("   Get real key from: https://aistudio.google.com/app/apikey")
    print("   Then update .env file")
else:
    print(f"✅ Found API key: {google_key[:20]}...")
    try:
        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={google_key}',
            json={'contents': [{'parts': [{'text': 'Say hello'}]}]},
            timeout=10
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            print(f"✅ Response: {text[:150]}")
        else:
            print(f"❌ Error response: {response.text[:300]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

# Test Cerebras
print("\n2️⃣ CEREBRAS API")
print("-" * 80)

cerebras_key = os.getenv('CEREBRAS_API_KEY')
if not cerebras_key or cerebras_key.startswith('your_'):
    print("⚠️  CEREBRAS_API_KEY is placeholder or missing")
    print("   Get real key from: https://console.cerebras.ai/")
    print("   Then update .env file")
else:
    print(f"✅ Found API key: {cerebras_key[:20]}...")
    try:
        response = requests.post(
            'https://api.cerebras.ai/v1/chat/completions',
            headers={'Authorization': f'Bearer {cerebras_key}'},
            json={
                'model': 'llama-3.3-70b',
                'messages': [{'role': 'user', 'content': 'Say hello'}]
            },
            timeout=10
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"✅ Response: {text[:150]}")
        else:
            print(f"❌ Error response: {response.text[:300]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "=" * 80)
print("📝 TO GET REAL KEYS:")
print("=" * 80)
print("  Google Gemini: https://aistudio.google.com/app/apikey (free tier)")
print("  Cerebras:      https://console.cerebras.ai/ (free tier)")
print("\nUpdate .env with real keys, then try dry-run tests:")
print("  python3 -u evaluation/run_experiments.py --model gemini-2.0-flash --benchmark benchmark/benchmark.json --dry-run")
print("  python3 -u evaluation/run_experiments.py --model llama-3.3-70b --benchmark benchmark/benchmark.json --dry-run")
