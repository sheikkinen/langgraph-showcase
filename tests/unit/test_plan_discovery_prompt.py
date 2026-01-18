"""Tests for plan_discovery prompt."""

from pathlib import Path

from yamlgraph.models.impl_agent_schemas import DiscoveryPlan, DiscoveryTask
from yamlgraph.utils.prompts import load_prompt


class TestPlanDiscoveryPrompt:
    """Tests for plan_discovery.yaml prompt structure."""

    def test_prompt_file_exists(self):
        """Prompt file exists and is loadable."""
        prompt_path = Path("prompts/impl-agent/plan_discovery.yaml")
        assert prompt_path.exists(), "plan_discovery.yaml not found"

        prompt = load_prompt("impl-agent/plan_discovery")
        assert "system" in prompt
        assert "user" in prompt
        assert "schema" in prompt

    def test_prompt_has_required_sections(self):
        """Prompt contains key instruction sections."""
        prompt = load_prompt("impl-agent/plan_discovery")
        system = prompt["system"]

        # Check for key sections
        assert "Available Tools" in system
        assert "Minimum Checklist" in system
        assert "Priority" in system

    def test_prompt_lists_core_tools(self):
        """Prompt documents core discovery tools."""
        prompt = load_prompt("impl-agent/plan_discovery")
        system = prompt["system"]

        # Core tools should be listed
        assert "list_modules" in system
        assert "get_structure" in system
        assert "find_tests" in system
        assert "get_callers" in system
        assert "find_similar_code" in system

    def test_schema_matches_discovery_plan(self):
        """Output schema is compatible with DiscoveryPlan model."""
        prompt = load_prompt("impl-agent/plan_discovery")
        schema = prompt["schema"]

        # Schema should have name and define tasks field
        assert "name" in schema
        assert schema["name"] == "DiscoveryPlan"
        assert "fields" in schema
        assert "tasks" in schema["fields"]

    def test_discovery_plan_accepts_valid_output(self):
        """DiscoveryPlan can parse expected LLM output format."""
        # Simulate LLM output
        llm_output = {
            "tasks": [
                {
                    "id": 1,
                    "task": "Find websearch module structure",
                    "tool": "get_structure",
                    "args": {"file_path": "yamlgraph/tools/websearch.py"},
                    "rationale": "Locate target function",
                    "priority": 1,
                },
                {
                    "id": 2,
                    "task": "Find callers of websearch",
                    "tool": "get_callers",
                    "args": {
                        "file_path": "yamlgraph/tools/websearch.py",
                        "function_name": "websearch",
                        "line": 10,
                    },
                    "rationale": "Understand dependencies",
                    "priority": 2,
                },
            ]
        }

        # Should parse successfully
        plan = DiscoveryPlan(tasks=[DiscoveryTask(**t) for t in llm_output["tasks"]])
        assert len(plan.tasks) == 2
        assert plan.tasks[0].tool == "get_structure"
        assert plan.tasks[1].priority == 2

    def test_minimum_checklist_coverage(self):
        """Prompt explicitly requires minimum discovery coverage."""
        prompt = load_prompt("impl-agent/plan_discovery")
        system = prompt["system"]

        # Minimum checklist items
        assert "Location" in system
        assert "Dependencies" in system
        assert "Tests" in system
        assert "Patterns" in system
