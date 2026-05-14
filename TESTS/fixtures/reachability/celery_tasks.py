"""
Fixture: Celery tasks (entry points) with reachable and dead helpers.

Reachable via @celery_app.task:
  - process_job (task entry point)
  - task_helper (called by process_job)

Unreachable:
  - orphan_task_helper (never called)
"""

import subprocess

from celery import Celery

celery_app = Celery("fixtures")


@celery_app.task
def process_job(payload):
    return task_helper(payload)


def task_helper(data):
    # ACR-QA-TEST: reachable via Celery task
    cmd = f"echo {data}"
    subprocess.run(cmd, shell=True)  # noqa: S602


def orphan_task_helper():
    # ACR-QA-TEST: dead code (unreachable Celery helper)
    import eval as _eval  # noqa: F401

    pass
