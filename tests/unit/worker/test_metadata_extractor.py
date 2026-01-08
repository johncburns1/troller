"""Unit tests for MetadataExtractor."""

from typing import Any


from troller.worker.activities.llm_metadata import MetadataExtractor


class MockToolUseBlock:
    """Mock ToolUseBlock from Claude SDK."""

    def __init__(self, name: str, input_data: dict[str, Any]):
        self.name = name
        self.input = input_data


class MockAssistantMessage:
    """Mock AssistantMessage from Claude SDK."""

    def __init__(self, content: list[Any], model: str | None = None):
        self.content = content
        self.model = model


class MockResultMessage:
    """Mock ResultMessage from Claude SDK."""

    def __init__(
        self,
        total_cost_usd: float | None = None,
        duration_ms: int = 0,
        duration_api_ms: int = 0,
        num_turns: int = 0,
        usage: dict[str, int] | None = None,
    ):
        self.total_cost_usd = total_cost_usd
        self.duration_ms = duration_ms
        self.duration_api_ms = duration_api_ms
        self.num_turns = num_turns
        self.usage = usage
        self.subtype = "result"


class TestMetadataExtractor:
    """Test suite for MetadataExtractor."""

    def test_extract_tools_used_returns_deduplicated_list(self) -> None:
        """extract_tools_used returns deduplicated list of tool names in order."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Bash", {"command": "ls"}),
                    MockToolUseBlock("Read", {"file_path": "test.py"}),
                    MockToolUseBlock("Bash", {"command": "pwd"}),  # Duplicate
                ]
            ),
        ]

        tools_used = extractor.extract_tools_used(messages)

        assert tools_used == ["Bash", "Read"]

    def test_extract_tools_used_handles_empty_messages(self) -> None:
        """extract_tools_used handles empty message list."""
        extractor = MetadataExtractor()

        tools_used = extractor.extract_tools_used([])

        assert tools_used == []

    def test_extract_tool_invocations_captures_bash_commands(self) -> None:
        """extract_tool_invocations captures actual bash commands."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Bash", {"command": "git status"}),
                    MockToolUseBlock("Bash", {"command": "npm install"}),
                ]
            ),
        ]

        invocations = extractor.extract_tool_invocations(messages)

        assert len(invocations) == 2
        assert invocations[0].tool == "Bash"
        assert invocations[0].details == "bash: git status"
        assert invocations[0].parameters == {"command": "git status"}
        assert invocations[1].tool == "Bash"
        assert invocations[1].details == "bash: npm install"
        assert invocations[1].parameters == {"command": "npm install"}

    def test_extract_tool_invocations_captures_skill_invocations(self) -> None:
        """extract_tool_invocations captures skill names and args."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Skill", {"skill": "feature-planner"}),
                    MockToolUseBlock(
                        "Skill", {"skill": "commit", "args": "-m 'Fix bug'"}
                    ),
                ]
            ),
        ]

        invocations = extractor.extract_tool_invocations(messages)

        assert len(invocations) == 2
        assert invocations[0].tool == "Skill"
        assert invocations[0].details == "skill: feature-planner"
        assert invocations[0].parameters == {"skill": "feature-planner"}
        assert invocations[1].tool == "Skill"
        assert invocations[1].details == "skill: commit -m 'Fix bug'"
        assert invocations[1].parameters == {"skill": "commit", "args": "-m 'Fix bug'"}

    def test_extract_tool_invocations_captures_read_operations(self) -> None:
        """extract_tool_invocations captures file paths for Read operations."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Read", {"file_path": "/src/main.py"}),
                    MockToolUseBlock("Read", {"file_path": "/tests/test_main.py"}),
                ]
            ),
        ]

        invocations = extractor.extract_tool_invocations(messages)

        assert len(invocations) == 2
        assert invocations[0].tool == "Read"
        assert invocations[0].details == "read: /src/main.py"
        assert invocations[0].parameters == {"file_path": "/src/main.py"}
        assert invocations[1].tool == "Read"
        assert invocations[1].details == "read: /tests/test_main.py"
        assert invocations[1].parameters == {"file_path": "/tests/test_main.py"}

    def test_extract_tool_invocations_captures_grep_searches(self) -> None:
        """extract_tool_invocations captures pattern and path for Grep."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Grep", {"pattern": "class Foo"}),
                    MockToolUseBlock(
                        "Grep", {"pattern": "def bar", "path": "/src/utils"}
                    ),
                ]
            ),
        ]

        invocations = extractor.extract_tool_invocations(messages)

        assert len(invocations) == 2
        assert invocations[0].tool == "Grep"
        assert invocations[0].details == "grep: class Foo"
        assert invocations[0].parameters == {"pattern": "class Foo"}
        assert invocations[1].tool == "Grep"
        assert invocations[1].details == "grep: def bar in /src/utils"
        assert invocations[1].parameters == {"pattern": "def bar", "path": "/src/utils"}

    def test_extract_tool_invocations_captures_glob_patterns(self) -> None:
        """extract_tool_invocations captures glob patterns."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Glob", {"pattern": "**/*.py"}),
                    MockToolUseBlock("Glob", {"pattern": "src/**/*.ts"}),
                ]
            ),
        ]

        invocations = extractor.extract_tool_invocations(messages)

        assert len(invocations) == 2
        assert invocations[0].tool == "Glob"
        assert invocations[0].details == "glob: **/*.py"
        assert invocations[0].parameters == {"pattern": "**/*.py"}
        assert invocations[1].tool == "Glob"
        assert invocations[1].details == "glob: src/**/*.ts"
        assert invocations[1].parameters == {"pattern": "src/**/*.ts"}

    def test_extract_tool_invocations_captures_task_agents(self) -> None:
        """extract_tool_invocations captures subagent type and description for Task."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock(
                        "Task",
                        {
                            "subagent_type": "Explore",
                            "description": "Find error handling",
                        },
                    ),
                ]
            ),
        ]

        invocations = extractor.extract_tool_invocations(messages)

        assert len(invocations) == 1
        assert invocations[0].tool == "Task"
        assert invocations[0].details == "task: Explore - Find error handling"
        assert invocations[0].parameters == {
            "subagent_type": "Explore",
            "description": "Find error handling",
        }

    def test_extract_tool_invocations_captures_todowrite(self) -> None:
        """extract_tool_invocations captures number of todos."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock(
                        "TodoWrite",
                        {
                            "todos": [
                                {"content": "Task 1", "status": "pending"},
                                {"content": "Task 2", "status": "pending"},
                            ]
                        },
                    ),
                ]
            ),
        ]

        invocations = extractor.extract_tool_invocations(messages)

        assert len(invocations) == 1
        assert invocations[0].tool == "TodoWrite"
        assert invocations[0].details == "todo: 2 items"
        assert invocations[0].parameters == {"num_todos": 2}

    def test_extract_tool_invocations_truncates_long_bash_commands(self) -> None:
        """extract_tool_invocations truncates very long bash commands to 100 chars."""
        extractor = MetadataExtractor()

        long_command = "a" * 150
        messages = [
            MockAssistantMessage([MockToolUseBlock("Bash", {"command": long_command})]),
        ]

        invocations = extractor.extract_tool_invocations(messages)

        assert len(invocations) == 1
        assert invocations[0].tool == "Bash"
        assert len(invocations[0].details) == len("bash: ") + 100
        assert (
            invocations[0].parameters["command"] == long_command
        )  # Full in parameters

    def test_generate_execution_flow_summarizes_skill_usage(self) -> None:
        """generate_execution_flow mentions skill invocation."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Skill", {"skill": "feature-planner"}),
                    MockToolUseBlock("Read", {"file_path": "test.py"}),
                ]
            ),
        ]

        flow = extractor.generate_execution_flow(messages, ["Skill", "Read"])

        assert "Invoked feature-planner skill" in flow

    def test_generate_execution_flow_includes_top_tools(self) -> None:
        """generate_execution_flow includes top 3 most-used tools with counts."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Read", {"file_path": "1.py"}),
                    MockToolUseBlock("Read", {"file_path": "2.py"}),
                    MockToolUseBlock("Read", {"file_path": "3.py"}),
                    MockToolUseBlock("Bash", {"command": "ls"}),
                    MockToolUseBlock("Bash", {"command": "pwd"}),
                    MockToolUseBlock("Grep", {"pattern": "foo"}),
                ]
            ),
        ]

        flow = extractor.generate_execution_flow(messages, ["Read", "Bash", "Grep"])

        assert "Read(3)" in flow
        assert "Bash(2)" in flow
        assert "Grep(1)" in flow

    def test_generate_execution_flow_limits_to_top_3_tools(self) -> None:
        """generate_execution_flow shows only top 3 tools when more exist."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [MockToolUseBlock("Read", {"file_path": f"{i}.py"}) for i in range(10)]
                + [MockToolUseBlock("Bash", {"command": "ls"}) for _ in range(5)]
                + [MockToolUseBlock("Grep", {"pattern": "foo"}) for _ in range(3)]
                + [MockToolUseBlock("Glob", {"pattern": "**/*.py"}) for _ in range(1)]
            ),
        ]

        flow = extractor.generate_execution_flow(
            messages, ["Read", "Bash", "Grep", "Glob"]
        )

        # Should have top 3: Read(10), Bash(5), Grep(3)
        # Should NOT have Glob(1)
        assert "Read(10)" in flow
        assert "Bash(5)" in flow
        assert "Grep(3)" in flow
        assert "Glob" not in flow

    def test_generate_execution_flow_truncates_to_200_chars(self) -> None:
        """generate_execution_flow truncates summary to 200 characters."""
        extractor = MetadataExtractor()

        # Create scenario that would generate a very long summary
        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Skill", {"skill": "feature-planner"}),
                ]
                + [
                    MockToolUseBlock("Read", {"file_path": f"file{i}.py"})
                    for i in range(100)
                ]
            ),
        ]

        flow = extractor.generate_execution_flow(messages, ["Skill", "Read"])

        assert len(flow) <= 200

    def test_extract_metadata_combines_all_data(self) -> None:
        """extract_metadata combines all metadata sources into LLMMetadata."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [
                    MockToolUseBlock("Skill", {"skill": "feature-planner"}),
                    MockToolUseBlock("Bash", {"command": "git status"}),
                    MockToolUseBlock("Read", {"file_path": "test.py"}),
                ],
                model="claude-sonnet-4-5-20250929",
            ),
        ]

        result_message = MockResultMessage(
            total_cost_usd=0.5,
            duration_ms=10000,
            duration_api_ms=8000,
            num_turns=5,
            usage={"input_tokens": 1000, "output_tokens": 500},
        )

        metadata = extractor.extract_metadata(messages, result_message)

        # Verify all fields are populated
        assert metadata.total_cost_usd == 0.5
        assert metadata.input_tokens == 1000
        assert metadata.output_tokens == 500
        assert metadata.duration_ms == 10000
        assert metadata.duration_api_ms == 8000
        assert metadata.num_turns == 5
        assert metadata.model == "claude-sonnet-4-5-20250929"
        assert metadata.tools_used == ["Skill", "Bash", "Read"]
        assert "Invoked feature-planner skill" in metadata.execution_flow
        assert len(metadata.tool_invocations) == 3
        assert metadata.tool_invocations[0].tool == "Skill"
        assert metadata.tool_invocations[1].tool == "Bash"
        assert metadata.tool_invocations[2].tool == "Read"

    def test_extract_metadata_handles_missing_result_message(self) -> None:
        """extract_metadata handles None result_message gracefully."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [MockToolUseBlock("Read", {"file_path": "test.py"})],
                model="claude-sonnet-4-5-20250929",
            ),
        ]

        metadata = extractor.extract_metadata(messages, None)

        # Verify defaults for missing data
        assert metadata.total_cost_usd is None
        assert metadata.input_tokens is None
        assert metadata.output_tokens is None
        assert metadata.duration_ms == 0
        assert metadata.duration_api_ms == 0
        assert metadata.num_turns == 0
        assert metadata.model == "claude-sonnet-4-5-20250929"
        assert metadata.tools_used == ["Read"]

    def test_extract_metadata_handles_missing_usage_data(self) -> None:
        """extract_metadata handles missing usage dict in result_message."""
        extractor = MetadataExtractor()

        messages = [
            MockAssistantMessage(
                [MockToolUseBlock("Read", {"file_path": "test.py"})],
            ),
        ]

        result_message = MockResultMessage(
            total_cost_usd=0.1,
            usage=None,  # No usage data
        )

        metadata = extractor.extract_metadata(messages, result_message)

        assert metadata.total_cost_usd == 0.1
        assert metadata.input_tokens is None
        assert metadata.output_tokens is None
