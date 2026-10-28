FROM python:3.12-slim
WORKDIR /app
COPY evaluation/verify_dataset.py evaluation/verify_dataset.py
COPY benchmark/benchmark_v3_escalated.json benchmark/benchmark_v3_escalated.json
COPY sandbox/logs/attacks.jsonl sandbox/logs/attacks.jsonl
COPY results/final_stats_v3.json results/final_stats_v3.json
USER 10001:10001
ENTRYPOINT ["python", "-I", "evaluation/verify_dataset.py"]
