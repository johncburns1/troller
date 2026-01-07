"""Temporal worker runner for issue resolution workflows.

This script starts a Temporal worker that processes workflows and activities
for autonomous GitHub issue resolution.
"""

import argparse
import asyncio
import logging
import sys

from temporalio.client import Client
from temporalio.worker import Worker

from troller.config import config
from troller.worker.activities.github_activities import fetch_issue
from troller.worker.activities.planning_activities import run_planning_agent
from troller.worker.data_converter import pydantic_data_converter
from troller.worker.workflows.issue_resolution import IssueResolutionWorkflow

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_worker(temporal_address: str, task_queue: str) -> None:
    """Start the Temporal worker.

    Args:
        temporal_address: Address of the Temporal server.
        task_queue: Name of the task queue to listen on.
    """
    logger.info(f"Connecting to Temporal at {temporal_address}")

    try:
        client = await Client.connect(
            temporal_address,
            data_converter=pydantic_data_converter,
        )

        logger.info(f"Starting worker on task queue: {task_queue}")

        worker = Worker(
            client,
            task_queue=task_queue,
            workflows=[IssueResolutionWorkflow],
            activities=[fetch_issue, run_planning_agent],
        )

        logger.info("Worker started successfully. Press Ctrl+C to stop.")
        await worker.run()

    except KeyboardInterrupt:
        logger.info("Shutting down worker...")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments with temporal_address and task_queue attributes.
    """
    parser = argparse.ArgumentParser(
        description="Start Temporal worker for issue resolution workflows",
    )

    parser.add_argument(
        "--temporal-address",
        default=config.temporal.address,
        help=f"Temporal server address (default: {config.temporal.address})",
    )

    parser.add_argument(
        "--task-queue",
        default=config.temporal.task_queue,
        help=f"Task queue name (default: {config.temporal.task_queue})",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_worker(args.temporal_address, args.task_queue))
