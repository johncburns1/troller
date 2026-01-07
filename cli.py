"""CLI for triggering issue resolution workflows.

This script provides a command-line interface to trigger Temporal workflows
for autonomous GitHub issue resolution.
"""

import argparse
import asyncio
import sys

from temporalio.client import Client

from troller.config import config
from troller.worker.data_converter import pydantic_data_converter
from troller.worker.workflows.data_structures import IssueResolutionWorkflowInput
from troller.worker.workflows.issue_resolution import IssueResolutionWorkflow


async def trigger_workflow(
    temporal_address: str,
    task_queue: str,
    repo_owner: str,
    repo_name: str,
    issue_number: int,
    target_branch: str | None,
) -> None:
    """Trigger the issue resolution workflow.

    Args:
        temporal_address: Address of the Temporal server.
        task_queue: Task queue name.
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        issue_number: GitHub issue number.
        target_branch: Target branch for the implementation.
    """
    print(f"Connecting to Temporal at {temporal_address}...")

    try:
        client = await Client.connect(
            temporal_address,
            data_converter=pydantic_data_converter,
        )

        workflow_input = IssueResolutionWorkflowInput(
            repo_owner=repo_owner,
            repo_name=repo_name,
            issue_number=issue_number,
            target_branch=target_branch,
        )

        workflow_id = f"issue-{repo_owner}-{repo_name}-{issue_number}"

        print(f"Starting workflow for {repo_owner}/{repo_name} issue #{issue_number}")
        print(f"Workflow ID: {workflow_id}\n")

        result = await client.execute_workflow(
            IssueResolutionWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=task_queue,
        )

        print("Workflow completed successfully!\n")
        print(f"Summary: {result.summary}\n")
        print("Steps:")
        for i, step in enumerate(result.steps, 1):
            status = "✓" if step.completed else " "
            print(f"  [{status}] {i}. {step.description}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Trigger issue resolution workflow",
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

    parser.add_argument(
        "--repo-owner",
        required=True,
        help="GitHub repository owner",
    )

    parser.add_argument(
        "--repo-name",
        required=True,
        help="GitHub repository name",
    )

    parser.add_argument(
        "--issue-number",
        type=int,
        required=True,
        help="GitHub issue number",
    )

    parser.add_argument(
        "--target-branch",
        help="Target branch for implementation (optional)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        trigger_workflow(
            args.temporal_address,
            args.task_queue,
            args.repo_owner,
            args.repo_name,
            args.issue_number,
            args.target_branch,
        )
    )
