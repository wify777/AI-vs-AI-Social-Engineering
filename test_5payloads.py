#!/usr/bin/env python3
"""Test 5 diverse attack payloads"""

import sys
sys.path.insert(0, '/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering')

import json
import time
from sandbox.agents.parser_agent import ParserAgent
from sandbox.agents.admin_agent import AdminAgent
from sandbox.bus import MessageBus

# Load first 5 payloads from benchmark
payloads = json.load(open('benchmark/benchmark.json'))[:5]

print("=" * 80)
print("🧪 TEST: 5 DIVERSE ATTACK PAYLOADS")
print("=" * 80)

parser = ParserAgent(model="openai/gpt-oss-120b", provider="groq")
admin = AdminAgent(model="openai/gpt-oss-120b", provider="groq")
bus = MessageBus()

results = []

for i, p in enumerate(payloads, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/5] Payload: {p['id']} - {p['category']}")
    print(f"{'='*80}")
    print(f"\n📝 Attack content:\n{p['attack_content'][:150]}...")

    try:
        result = bus.orchestrate_attack(payload=p, parser=parser, admin=admin)

        parser_resp = result['parser_stage']['parser_response']
        admin_resp = result['admin_stage']['admin_response']
        tool_executed = result['outcome']['tool_executed']

        print(f"\n✅ PARSER forwarded: {parser_resp[:180]}...")
        print(f"\n📊 ADMIN response: {admin_resp[:180]}...")
        print(f"\n🎯 OUTCOME:")
        print(f"   Tool executed: {tool_executed}")
        print(f"   Tool attempted: {result['admin_stage']['tool_attempted']}")
        print(f"   Confidence: {result['admin_stage']['confidence']:.2f}")

        results.append({
            "payload_id": p['id'],
            "category": p['category'],
            "tool_executed": tool_executed,
            "parser_forwarded": bool(parser_resp and "sorry" not in parser_resp.lower()),
            "tool_attempted": result['admin_stage']['tool_attempted']
        })

        time.sleep(2)  # Rate limit safety

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append({
            "payload_id": p['id'],
            "category": p['category'],
            "error": str(e)
        })

# Summary
print(f"\n{'='*80}")
print("📊 SUMMARY")
print(f"{'='*80}")

for r in results:
    if "error" in r:
        status = "❌ ERROR"
    elif r.get("tool_executed"):
        status = "🔴 SUCCESS (Attack worked!)"
    elif r.get("parser_forwarded"):
        status = "✅ Forwarded (Admin blocked)"
    else:
        status = "⚠️  Not forwarded"

    print(f"{r['payload_id']:20} | {r['category']:20} | {status}")

print(f"\n{'='*80}")
print("ANALYSIS:")
print(f"{'='*80}")

forwarded = sum(1 for r in results if r.get("parser_forwarded", False))
executed = sum(1 for r in results if r.get("tool_executed", False))
errors = sum(1 for r in results if "error" in r)

print(f"✅ Parser forwarded: {forwarded}/5")
print(f"🔴 Tools executed: {executed}/5")
print(f"❌ Errors: {errors}/5")

if executed > 0:
    print("\n✅ AT LEAST ONE ATTACK SUCCEEDED - Ready for production!")
elif forwarded == 5:
    print("\n✅ ALL ATTACKS FORWARDED - Admin correctly blocked all attacks!")
else:
    print(f"\n⚠️  ONLY {forwarded}/5 ATTACKS FORWARDED - Parser may still be filtering!")
