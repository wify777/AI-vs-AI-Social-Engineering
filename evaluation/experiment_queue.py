"""
Experiment queue with checkpoint-based recovery.

Key features:
1. Enqueue all runs (900 experiments)
2. Save state after each run
3. On restart: load last checkpoint, continue from next item
4. Respect API rate limits
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import threading


@dataclass
class ExperimentJob:
    """Single experiment job"""

    job_id: str
    payload_id: str
    model_admin: str
    model_parser: str
    category: str
    condition: str
    repetition: int
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict] = None
    error: Optional[str] = None
    timestamp_created: Optional[str] = None
    timestamp_completed: Optional[str] = None


class ExperimentQueue:
    """Manage job queue with checkpoint recovery"""

    def __init__(
        self,
        model_name: str = "default",
        queue_file: Optional[str] = None,
        checkpoint_file: Optional[str] = None,
        max_retries: int = 3,
    ):
        # Generate model-specific paths
        model_safe = model_name.replace("/", "_").replace(":", "_")

        if queue_file is None:
            Path("evaluation/queues").mkdir(parents=True, exist_ok=True)
            queue_file = f"evaluation/queues/queue_{model_safe}.jsonl"

        if checkpoint_file is None:
            Path("evaluation/checkpoints").mkdir(parents=True, exist_ok=True)
            checkpoint_file = f"evaluation/checkpoints/checkpoint_{model_safe}.json"

        self.model_name = model_name
        self.queue_file = Path(queue_file)
        self.checkpoint_file = Path(checkpoint_file)
        self.max_retries = max_retries

        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        self.jobs: List[ExperimentJob] = []
        self.checkpoint: Dict = {}

        self.load_checkpoint()

    def add_job(self, job: ExperimentJob) -> None:
        """Add job to queue"""
        job.timestamp_created = datetime.utcnow().isoformat() + "Z"
        self.jobs.append(job)
        self._persist_job(job)

    def _persist_job(self, job: ExperimentJob) -> None:
        """Write job to queue file"""
        with open(self.queue_file, "a") as f:
            f.write(json.dumps(asdict(job)) + "\n")

    def save_checkpoint(self, current_index: int, total: int) -> None:
        """Save recovery checkpoint"""
        self.checkpoint = {
            "last_completed_index": current_index,
            "total_jobs": total,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "progress_pct": (current_index / total * 100) if total > 0 else 0,
        }

        with open(self.checkpoint_file, "w") as f:
            json.dump(self.checkpoint, f, indent=2)

        print(
            f"✅ Checkpoint: {current_index}/{total} "
            f"({self.checkpoint['progress_pct']:.1f}% complete)"
        )

    def load_checkpoint(self) -> int:
        """Load last checkpoint"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                self.checkpoint = json.load(f)

            last_idx = self.checkpoint.get("last_completed_index", 0)
            total = self.checkpoint.get("total_jobs", 0)
            pct = self.checkpoint.get("progress_pct", 0)

            print(f"✅ Loaded checkpoint: {last_idx}/{total} ({pct:.1f}% complete)")
            return last_idx

        return 0

    def get_next_job(self) -> Optional[ExperimentJob]:
        """Get next pending job"""
        last_idx = self.load_checkpoint()

        if last_idx < len(self.jobs):
            return self.jobs[last_idx]

        return None

    def mark_completed(self, job_id: str, result: Dict) -> None:
        """Mark job as completed"""
        for job in self.jobs:
            if job.job_id == job_id:
                job.status = "completed"
                job.result = result
                job.timestamp_completed = datetime.utcnow().isoformat() + "Z"
                self._persist_job(job)
                break

    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed"""
        for job in self.jobs:
            if job.job_id == job_id:
                job.status = "failed"
                job.error = error
                self._persist_job(job)
                break

    def stats(self) -> Dict:
        """Queue statistics"""
        completed = sum(1 for j in self.jobs if j.status == "completed")
        failed = sum(1 for j in self.jobs if j.status == "failed")
        pending = sum(1 for j in self.jobs if j.status == "pending")

        return {
            "total": len(self.jobs),
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress_pct": (completed / len(self.jobs) * 100) if self.jobs else 0,
        }


class RateLimiter:
    """Respect API rate limits (RPM, RPD) with minimum inter-request delay"""

    def __init__(self, rpm: int = 20, rpd: int = 1000, min_delay_ms: float = 500):
        self.rpm = rpm  # Requests per minute (conservative, Groq allows 1000)
        self.rpd = rpd  # Requests per day
        self.min_delay_ms = min_delay_ms  # Minimum milliseconds between requests (500ms = 2 req/sec max)
        self.requests_this_minute = 0
        self.requests_today = 0
        self.last_minute_reset = time.time()
        self.last_day_reset = time.time()
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait_if_needed(self) -> None:
        """Block until rate limit allows next request"""
        with self.lock:
            now = time.time()

            # Minimum delay between requests
            elapsed_since_last = (now - self.last_request_time) * 1000  # Convert to ms
            if elapsed_since_last < self.min_delay_ms:
                sleep_ms = self.min_delay_ms - elapsed_since_last
                time.sleep(sleep_ms / 1000.0)
                now = time.time()

            # Reset minute counter
            if now - self.last_minute_reset > 60:
                self.requests_this_minute = 0
                self.last_minute_reset = now

            # Reset day counter (24 hours)
            if now - self.last_day_reset > 86400:
                self.requests_today = 0
                self.last_day_reset = now

            # Check RPM limit
            if self.requests_this_minute >= self.rpm:
                sleep_time = 60 - (now - self.last_minute_reset)
                if sleep_time > 0:
                    print(f"⏸️  RPM limit hit. Sleeping {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    self.requests_this_minute = 0
                    self.last_minute_reset = time.time()

            # Check RPD limit
            if self.requests_today >= self.rpd:
                print(f"❌ RPD limit ({self.rpd}) exceeded. Cannot proceed today.")
                raise RuntimeError("RPD limit exceeded")

            # Increment counters and track request time
            self.requests_this_minute += 1
            self.requests_today += 1
            self.last_request_time = time.time()

    def status(self) -> Dict:
        """Current rate limit status"""
        return {
            "rpm": f"{self.requests_this_minute}/{self.rpm}",
            "rpd": f"{self.requests_today}/{self.rpd}",
        }
