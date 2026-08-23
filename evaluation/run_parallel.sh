#!/bin/bash
# Parallel v2 experiments across Groq + Google + Cerebras
# Run 540 scenarios per provider for 2,160+ total experiments

set -e

cd /Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering
source .venv/bin/activate

echo "════════════════════════════════════════════════════════════"
echo "🚀 PARALLEL V2 EXPERIMENTS"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Timeline:"
echo "  • Groq (4 models, sequential): ~90 min total"
echo "  • Google (2 models, parallel): ~60 min total"
echo "  • Cerebras (1 model, parallel): ~45 min"
echo ""
echo "Expected finish: ~90 minutes (Groq sequential is bottleneck)"
echo ""

# Terminal 1: Groq models (sequential due to rate limits)
echo "Starting Groq models (sequential queue)..."
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model qwen/qwen3.6-27b \
  --benchmark benchmark/benchmark.json > logs/run_qwen.log 2>&1 &
QWEN_PID=$!

PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model openai/gpt-oss-20b \
  --benchmark benchmark/benchmark.json > logs/run_gpt20b.log 2>&1 &
GPT20B_PID=$!

# Terminal 2: Google Gemini (if API key is set)
if [ -n "$GOOGLE_API_KEY" ] && [[ ! "$GOOGLE_API_KEY" =~ ^your_ ]]; then
  echo "Starting Google Gemini models (parallel)..."
  PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
    --model gemini-2.0-flash \
    --benchmark benchmark/benchmark.json > logs/run_gemini_flash.log 2>&1 &
  GEMINI_PID=$!
else
  echo "⏭️  Skipping Google (API key not configured)"
  GEMINI_PID=""
fi

# Terminal 3: Cerebras (if API key is set)
if [ -n "$CEREBRAS_API_KEY" ] && [[ ! "$CEREBRAS_API_KEY" =~ ^your_ ]]; then
  echo "Starting Cerebras (parallel)..."
  PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
    --model llama-3.3-70b \
    --benchmark benchmark/benchmark.json > logs/run_cerebras.log 2>&1 &
  CEREBRAS_PID=$!
else
  echo "⏭️  Skipping Cerebras (API key not configured)"
  CEREBRAS_PID=""
fi

echo ""
echo "Process IDs:"
echo "  qwen=$QWEN_PID"
echo "  gpt20b=$GPT20B_PID"
[ -n "$GEMINI_PID" ] && echo "  gemini=$GEMINI_PID" || echo "  gemini=SKIPPED"
[ -n "$CEREBRAS_PID" ] && echo "  cerebras=$CEREBRAS_PID" || echo "  cerebras=SKIPPED"

echo ""
echo "⏱️  Waiting for all to complete..."
echo ""

# Wait for all running processes
for pid in $QWEN_PID $GPT20B_PID $GEMINI_PID $CEREBRAS_PID; do
  [ -n "$pid" ] && wait $pid
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ ALL EXPERIMENTS COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Results summary:"

# Count total experiments
TOTAL_RUNS=$(jq -s 'length' sandbox/logs/attacks.jsonl 2>/dev/null || echo "0")
echo "  • Total runs logged: $TOTAL_RUNS"
echo "  • Check sandbox/logs/attacks.jsonl for detailed results"
echo ""
echo "Analysis:"
echo "  python3 analysis/heatmap.py"
echo "  python3 evaluation/analysis_pipeline.py"
