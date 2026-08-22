"""
Combine all seed payloads into single benchmark.json
"""

import json
from pathlib import Path


def build_benchmark(
    seed_dir: str = "payloads/seed", output_file: str = "benchmark/benchmark.json"
):
    """Combine all seed payloads into benchmark"""

    all_payloads = []
    payload_files = sorted(Path(seed_dir).glob("*.json"))

    for pfile in payload_files:
        with open(pfile, "r") as f:
            payloads = json.load(f)
            all_payloads.extend(payloads)

    # Write combined benchmark
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(all_payloads, f, indent=2)

    print(f"✅ Built benchmark: {len(all_payloads)} payloads → {output_file}")
    return all_payloads


if __name__ == "__main__":
    build_benchmark()
