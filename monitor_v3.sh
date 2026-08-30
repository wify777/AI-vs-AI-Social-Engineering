#!/bin/bash

# V3 Live Monitor - run in separate terminal
# Shows real-time progress of full V3 experiment run

while true; do
    clear
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "V3 LIVE MONITOR"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    date "+%Y-%m-%d %H:%M:%S"
    echo ""

    python3 << 'MONITOR_SCRIPT'
import json
from collections import defaultdict
import os

try:
    logfile = 'sandbox/logs/attacks.jsonl'
    if not os.path.exists(logfile):
        print("⏳ Waiting for logs to be created...")
    else:
        logs = []
        with open(logfile) as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except:
                        pass

        if logs:
            total = len(logs)
            success = sum(1 for l in logs if l.get('tool_executed', False))
            asr = success / total * 100 if total > 0 else 0

            print(f"📊 OVERALL STATS")
            print(f"  Total experiments:  {total:,} / 4,860 ({total/4860*100:.1f}%)")
            print(f"  Tool executions:    {success:,}")
            print(f"  Attack Success Rate (ASR): {asr:.2f}% ({success}/{total})")
            print()

            # By model
            by_model = defaultdict(lambda: {'total': 0, 'success': 0})
            for log in logs:
                model = log.get('model_admin', '?')
                by_model[model]['total'] += 1
                if log.get('tool_executed', False):
                    by_model[model]['success'] += 1

            print(f"📈 BY MODEL (ASR %)")
            for model in sorted(by_model.keys()):
                stats = by_model[model]
                asr = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
                progress = stats['total'] / (60 * 3 * 3)  # 60 payloads × 3 conditions × 3 reps
                bar_len = int(progress * 20)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                print(f"  {model:35s} {asr:6.2f}% [{bar}] {stats['success']:3d}/{stats['total']:3d}")

            print()
            print(f"💾 Log file: {logfile} ({os.path.getsize(logfile):,} bytes)")
        else:
            print("⏳ Logs created but no entries yet...")

except Exception as e:
    print(f"Error reading logs: {e}")
    import traceback
    traceback.print_exc()

MONITOR_SCRIPT

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Refreshing in 30 seconds... (Ctrl+C to stop)"
    echo ""

    sleep 30
done
