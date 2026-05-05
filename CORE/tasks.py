"""
Celery task definitions for ACR-QA.

Worker start:
    celery -A CORE.tasks worker --loglevel=info --concurrency=4
"""

import logging
import os
import sys
from pathlib import Path

from celery import Celery

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

_redis_url = os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/0")

celery_app = Celery(
    "acrqa",
    broker=_redis_url,
    backend=_redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=86400,  # results kept 24h
    worker_prefetch_multiplier=1,  # fair dispatch — one task at a time per worker
)


@celery_app.task(bind=True, name="acrqa.run_analysis")
def run_analysis_task(
    self,
    target_dir: str,
    repo_name: str = "local",
    pr_number: int | None = None,
    limit: int | None = None,
) -> dict:
    """Run the full ACR-QA analysis pipeline as a background task.

    Returns dict with run_id and finding counts on success.
    The task ID can be used to poll status via GET /v1/scans/{job_id}.
    """
    from CORE.main import AnalysisPipeline

    self.update_state(state="STARTED", meta={"status": "running", "repo": repo_name})
    logger.info("Celery task %s: starting analysis for %s", self.request.id, repo_name)

    try:
        pipeline = AnalysisPipeline(target_dir=target_dir)
        result = pipeline.run(repo_name=repo_name, pr_number=pr_number, limit=limit)

        if result is None:
            return {"status": "failed", "error": "Rate limited or pipeline returned None"}

        run_id, findings_count = result if isinstance(result, tuple) else (result, None)
        return {
            "status": "completed",
            "run_id": run_id,
            "findings_count": findings_count,
            "repo": repo_name,
        }
    except Exception as exc:
        logger.exception("Celery task %s failed: %s", self.request.id, exc)
        self.update_state(state="FAILURE", meta={"status": "failed", "error": str(exc)})
        raise
