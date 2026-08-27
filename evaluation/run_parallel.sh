#!/bin/bash
# Parallel v2 experiments across Groq + Google (updated models)
# Run 540 scenarios per provider for 1,080+ total experiments

set -e

cd /Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering
source .venv/bin/activate

echo "════════════════════════════════════════════════════════════"
echo "🚀 PARALLEL V2 EXPERIMENTS (UPDATED)"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Models:"
echo "  • Groq (4): qwen, gpt-oss-20b, gpt-oss-120b, allam"
echo "  • Google (2): gemini-3.6-flash, gemini-flash-latest"
echo ""
echo "Timeline:"
echo "  • Groq (4 models, sequential): ~90 min total"
echo "  • Google (2 models, parallel): ~50 min"
echo ""
echo "Expected finish: ~90 minutes (Groq sequential is bottleneck)"
echo ""

# Ensure logs directory exists
mkdir -p logs

# Terminal 1: Groq models (sequential due to rate limits)
echo "Starting Groq models (sequential queue)..."
PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
  --model qwen/qwen3.6-27b \
  --benchmark benchmark/benchmark.json > logs/run_qwen.log 2>&1 &
QWEN_PID=$!

# Terminal 2: Google Gemini (if API key is set)
if [ -n "$GOOGLE_API_KEY" ] && [[ ! "$GOOGLE_API_KEY" =~ ^your_ ]]; then
  echo "Starting Google Gemini models (parallel)..."
  PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
    --model gemini-3.6-flash \
    --benchmark benchmark/benchmark.json > logs/run_gemini_3_6_flash.log 2>&1 &
  GEMINI_36_PID=$!

  PYTHONPATH=$PWD python3 -u evaluation/run_experiments.py \
    --model gemini-flash-latest \
    --benchmark benchmark/benchmark.json > logs/run_gemini_flash_latest.log 2>&1 &
  GEMINI_LATEST_PID=$!
else
  echo "⏭️  Skipping Google (API key not configured)"
  GEMINI_36_PID=""
  GEMINI_LATEST_PID=""
fi

echo ""
echo "Process IDs:"
echo "  qwen=$QWEN_PID"
[ -n "$GEMINI_36_PID" ] && echo "  gemini-3.6-flash=$GEMINI_36_PID" || echo "  gemini-3.6-flash=SKIPPED"
[ -n "$GEMINI_LATEST_PID" ] && echo "  gemini-flash-latest=$GEMINI_LATEST_PID" || echo "  gemini-flash-latest=SKIPPED"

echo ""
echo "⏱️  Waiting for all to complete..."
echo ""

# Wait for all running processes
for pid in $QWEN_PID $GEMINI_36_PID $GEMINI_LATEST_PID; do
  [ -n "$pid" ] && wait $pid 2>/dev/null || true
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
