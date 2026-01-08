"""Metadata extraction from Claude Agent SDK messages.

Pure logic for extracting and structuring LLM metadata from SDK messages.
Separated for testability and single responsibility.
"""

from typing import Any

from troller.worker.activities.activity_outputs import (
    LLMMetadataOutput,
    ToolInvocationOutput,
)


class MetadataExtractor:
    """Extracts structured metadata from Claude Agent SDK messages.

    This class contains pure extraction logic with no dependencies,
    making it easy to test in isolation.
    """

    def extract_metadata(
        self, messages: list[Any], result_message: Any
    ) -> LLMMetadataOutput:
        """Extract LLM metadata from SDK messages and result.

        Args:
            messages: List of SDK messages from the query execution.
            result_message: The final ResultMessage with cost and usage info.

        Returns:
            LLMMetadataOutput object with extracted information.
        """
        # Extract from ResultMessage
        total_cost = None
        duration_ms = 0
        duration_api_ms = 0
        num_turns = 0
        input_tokens = None
        output_tokens = None

        if result_message:
            total_cost = getattr(result_message, "total_cost_usd", None)
            duration_ms = getattr(result_message, "duration_ms", 0)
            duration_api_ms = getattr(result_message, "duration_api_ms", 0)
            num_turns = getattr(result_message, "num_turns", 0)

            # Parse usage dict for tokens
            usage = getattr(result_message, "usage", None)
            if usage and isinstance(usage, dict):
                input_tokens = usage.get("input_tokens")
                output_tokens = usage.get("output_tokens")

        # Extract model from AssistantMessage
        model = None
        for msg in messages:
            if hasattr(msg, "model"):
                model = msg.model
                break

        # Track ALL tools used
        tools_used = self.extract_tools_used(messages)

        # Generate execution flow summary
        execution_flow = self.generate_execution_flow(messages, tools_used)

        # Extract detailed tool invocations for audit trail
        tool_invocations = self.extract_tool_invocations(messages)

        return LLMMetadataOutput(
            total_cost_usd=total_cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            duration_api_ms=duration_api_ms,
            num_turns=num_turns,
            model=model,
            tools_used=tools_used,
            execution_flow=execution_flow,
            tool_invocations=tool_invocations,
        )

    def extract_tools_used(self, messages: list[Any]) -> list[str]:
        """Extract all tool names used during execution.

        Args:
            messages: List of SDK messages from the query execution.

        Returns:
            Deduplicated list of tool names in order of first use.
        """
        tools_seen = []
        tools_set = set()

        for message in messages:
            # Check if this is an AssistantMessage with content blocks
            if hasattr(message, "content") and isinstance(message.content, list):
                for block in message.content:
                    # Check if this is a ToolUseBlock
                    if hasattr(block, "name") and hasattr(block, "input"):
                        tool_name = block.name
                        if tool_name not in tools_set:
                            tools_seen.append(tool_name)
                            tools_set.add(tool_name)

        return tools_seen

    def generate_execution_flow(
        self, messages: list[Any], tools_used: list[str]
    ) -> str:
        """Generate auto-generated execution flow summary.

        Args:
            messages: List of SDK messages from the query execution.
            tools_used: List of tools used during execution.

        Returns:
            Brief summary of execution flow (under 200 characters).
        """
        # Count tool usage
        tool_counts: dict[str, int] = {}
        for message in messages:
            if hasattr(message, "content") and isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, "name") and hasattr(block, "input"):
                        tool_name = block.name
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        # Build summary
        summary_parts = []

        # Check for skill invocation
        if "Skill" in tool_counts:
            summary_parts.append("Invoked feature-planner skill")

        # Add top tool usage (limit to 3 most used)
        top_tools = sorted(
            [(name, count) for name, count in tool_counts.items() if name != "Skill"],
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        if top_tools:
            tool_usage = ", ".join([f"{name}({count})" for name, count in top_tools])
            summary_parts.append(f"used {tool_usage}")

        summary = (
            ", ".join(summary_parts) if summary_parts else "Executed planning task"
        )

        # Truncate to 200 characters
        return summary[:200]

    def extract_tool_invocations(
        self, messages: list[Any]
    ) -> list[ToolInvocationOutput]:
        """Extract detailed audit trail of all tool invocations.

        Args:
            messages: List of SDK messages from the query execution.

        Returns:
            List of ToolInvocationOutput objects with detailed parameters.
        """
        invocations: list[ToolInvocationOutput] = []

        for message in messages:
            # Check if this is an AssistantMessage with content blocks
            if hasattr(message, "content") and isinstance(message.content, list):
                for block in message.content:
                    # Check if this is a ToolUseBlock
                    if hasattr(block, "name") and hasattr(block, "input"):
                        tool_name = block.name
                        tool_input = block.input

                        # Extract key parameters based on tool type
                        details = ""
                        parameters: dict[str, Any] = {}

                        if tool_name == "Bash" and isinstance(tool_input, dict):
                            command = tool_input.get("command", "")
                            details = f"bash: {command[:100]}"
                            parameters = {"command": command}

                        elif tool_name == "Skill" and isinstance(tool_input, dict):
                            skill = tool_input.get("skill", "")
                            args = tool_input.get("args", "")
                            details = f"skill: {skill}" + (f" {args}" if args else "")
                            parameters = {"skill": skill}
                            if args:
                                parameters["args"] = args

                        elif tool_name == "Read" and isinstance(tool_input, dict):
                            file_path = tool_input.get("file_path", "")
                            details = f"read: {file_path}"
                            parameters = {"file_path": file_path}

                        elif tool_name == "Grep" and isinstance(tool_input, dict):
                            pattern = tool_input.get("pattern", "")
                            path = tool_input.get("path", "")
                            details = f"grep: {pattern}" + (
                                f" in {path}" if path else ""
                            )
                            parameters = {"pattern": pattern}
                            if path:
                                parameters["path"] = path

                        elif tool_name == "Glob" and isinstance(tool_input, dict):
                            pattern = tool_input.get("pattern", "")
                            details = f"glob: {pattern}"
                            parameters = {"pattern": pattern}

                        elif tool_name == "Task" and isinstance(tool_input, dict):
                            subagent_type = tool_input.get("subagent_type", "")
                            description = tool_input.get("description", "")
                            details = f"task: {subagent_type} - {description}"
                            parameters = {
                                "subagent_type": subagent_type,
                                "description": description,
                            }

                        elif tool_name == "TodoWrite" and isinstance(tool_input, dict):
                            todos = tool_input.get("todos", [])
                            details = f"todo: {len(todos)} items"
                            parameters = {"num_todos": len(todos)}

                        elif tool_name == "StructuredOutput":
                            details = "structured output"
                            parameters = {}

                        else:
                            # Generic fallback for unknown tools
                            details = f"{tool_name.lower()}"
                            parameters = (
                                tool_input if isinstance(tool_input, dict) else {}
                            )

                        invocations.append(
                            ToolInvocationOutput(
                                tool=tool_name, details=details, parameters=parameters
                            )
                        )

        return invocations
