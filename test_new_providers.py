#!/usr/bin/env python3
"""Test Google Gemini API (updated models)"""

import sys
sys.path.insert(0, '/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering')

from dotenv import load_dotenv
import os
import requests

load_dotenv()

print("=" * 80)
print("🧪 TESTING GOOGLE GEMINI API (CURRENT MODELS)")
print("=" * 80)

google_key = os.getenv('GOOGLE_API_KEY')
if not google_key or google_key.startswith('your_'):
    print("⚠️  GOOGLE_API_KEY is placeholder or missing")
    print("   Get real key from: https://aistudio.google.com/app/apikey")
    print("   Then update .env file: GOOGLE_API_KEY=your_actual_key")
else:
    print(f"✅ Found API key: {google_key[:20]}...")

    models = [
        "gemini-3.6-flash",
        "gemini-flash-latest"
    ]

    for model in models:
        print(f"\nTesting {model}:")
        print("-" * 80)

        try:
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={google_key}',
                json={'contents': [{'parts': [{'text': 'Say hello briefly'}]}]},
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

print("\n" + "=" * 80)
print("✅ ACTIVE MODELS:")
print("=" * 80)
print("  Groq (4):     openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.6-27b, allam-2-7b")
print("  Google (2):   gemini-3.6-flash, gemini-flash-latest")
print("\nREMOVED:")
print("  Cerebras:     (paid tier - discontinued)")
print("  Old Google:   gemini-2.0-flash, gemini-2.0-flash-lite, gemini-2.5-flash (deprecated)")
