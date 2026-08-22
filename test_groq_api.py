#!/usr/bin/env python3
"""
Test Groq API connection and list available models.
Run this after updating .env with real API key.
"""

import requests
import sys

def get_api_key():
    """Read Groq API key from .env"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('GROQ_API_KEY='):
                    key = line.split('=', 1)[1].strip()
                    return key
    except FileNotFoundError:
        print("❌ .env file not found")
        return None
    return None

def test_key_format(key):
    """Validate API key format"""
    print("=" * 70)
    print("1️⃣  KEY FORMAT CHECK")
    print("=" * 70)

    if not key:
        print("❌ API key is empty")
        return False

    if key == "your_groq_key_here":
        print("❌ API key is placeholder (your_groq_key_here)")
        return False

    print(f"✓ Key length: {len(key)} chars")
    print(f"✓ Starts with: {key[:8]}")
    print(f"✓ Ends with: ...{key[-4:]}")

    if len(key) >= 50 and key.startswith('gsk_'):
        print("✅ Key format looks VALID")
        return True
    else:
        print("❌ Key format invalid (should be 50+ chars, start with 'gsk_')")
        return False

def list_models(key):
    """List available Groq models"""
    print("\n" + "=" * 70)
    print("2️⃣  AVAILABLE MODELS")
    print("=" * 70)

    try:
        response = requests.get(
            'https://api.groq.com/openai/v1/models',
            headers={'Authorization': f'Bearer {key}'},
            timeout=10
        )

        if response.status_code == 200:
            models = response.json().get('data', [])
            print(f"✅ Connected to Groq API ({len(models)} models available)\n")

            print("Available models:")
            for model in models:
                model_id = model.get('id', 'unknown')
                print(f"  • {model_id}")

            return models
        elif response.status_code == 401:
            print("❌ 401 Unauthorized - API key invalid")
            return None
        else:
            print(f"❌ Error {response.status_code}: {response.text[:200]}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - check internet or Groq status")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_chat_completion(key, model_id):
    """Test chat completion with specific model"""
    print("\n" + "=" * 70)
    print(f"3️⃣  TEST CHAT COMPLETION ({model_id})")
    print("=" * 70)

    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}'},
            json={
                'model': model_id,
                'messages': [{'role': 'user', 'content': 'Say hello in one sentence'}],
                'max_tokens': 50
            },
            timeout=30
        )

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"✅ Model {model_id} works!")
            print(f"Response: {content}")
            return True
        elif response.status_code == 404:
            print(f"❌ 404 - Model {model_id} not found")
            return False
        elif response.status_code == 429:
            print(f"⚠️  429 - Rate limit exceeded (try again later)")
            return False
        else:
            print(f"❌ Error {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("\n" + "=" * 70)
    print("GROQ API DIAGNOSTIC TEST")
    print("=" * 70 + "\n")

    # Get API key
    key = get_api_key()
    if not key:
        print("❌ Could not read API key from .env")
        sys.exit(1)

    # Check key format
    if not test_key_format(key):
        print("\n⚠️  Update .env with real Groq API key from https://console.groq.com/keys")
        sys.exit(1)

    # List models
    models = list_models(key)
    if not models:
        print("\n⚠️  Could not connect to Groq API")
        sys.exit(1)

    # Test first working model
    working_model = None
    for model in models:
        model_id = model.get('id')
        if test_chat_completion(key, model_id):
            working_model = model_id
            break

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if working_model:
        print(f"✅ Groq API fully functional")
        print(f"✅ Working model: {working_model}")
        print(f"\nTo use in M6, update:")
        print(f"  evaluation/run_all_models.py:")
        print(f"    API_MODELS = [\"{working_model}\"]")
        print(f"\nThen run: python3 evaluation/run_all_models.py --api-only")
    else:
        print("❌ No working models found")
        print("Try again later or check https://status.groq.com")

if __name__ == "__main__":
    main()
