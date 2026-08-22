#!/bin/bash
# M5 Local Models Execution Script
# Runs all local models with checkpoint recovery

set -e

cd /Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering

# Activate venv
source .venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH=/Users/akhmadbek/Desktop/AI-vs-AI-Social-Engineering

# Clear old checkpoint if needed (for fresh run)
# rm -f evaluation/checkpoint.json

echo "════════════════════════════════════════════════════"
echo "M5: LOCAL MODELS EXECUTION"
echo "════════════════════════════════════════════════════"
echo ""
echo "Models: mistral:7b-instruct-q4_K_M"
echo "Total payloads: 16 × 3 conditions × 3 reps = 144 jobs per model"
echo "Estimated time: 1-2 hours"
echo ""
echo "════════════════════════════════════════════════════"
echo ""

# Run M5 (local models only)
python3 evaluation/run_all_models.py --local-only

echo ""
echo "════════════════════════════════════════════════════"
echo "✅ M5 COMPLETE"
echo "════════════════════════════════════════════════════"
echo ""
echo "Results in: sandbox/logs/attacks.jsonl"
echo "Execution log: results/execution_log.json"
echo ""
