"""Tests for agent node LLM configuration.

Bug: Agent nodes ignore provider/temperature/model configuration;
create_llm() is called with defaults only. This makes agents inconsistent
with other node types and can break mixed-provider graphs.
"""

from unittest.mock import MagicMock, patch


class TestAgentLLMConfiguration:
    """Tests for agent node LLM configuration handling."""

    def test_agent_uses_provider_from_prompt_yaml(self) -> None:
        """Agent should use provider from prompt YAML."""
        from yamlgraph.tools.agent import create_agent_node

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            # Prompt YAML specifies provider
            mock_load.return_value = {
                "system": "You are helpful.",
                "user": "Do something with {input}",
                "provider": "openai",
                "model": "gpt-4o",
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.return_value = MagicMock(content="Done", tool_calls=[])
            mock_create_llm.return_value = mock_llm

            # Create and execute agent node
            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={"tools": []},
                tools={},
            )

            # Execute with minimal state
            node_fn({"input": "test input"})

            # BUG: create_llm() is called with no arguments
            mock_create_llm.assert_called_once()
            call_kwargs = mock_create_llm.call_args.kwargs

            # These assertions will FAIL because agent ignores config
            assert call_kwargs.get("provider") == "openai", (
                f"Agent should use provider from YAML. "
                f"Got call kwargs: {call_kwargs}"
            )

    def test_agent_uses_model_from_prompt_yaml(self) -> None:
        """Agent should use model from prompt YAML."""
        from yamlgraph.tools.agent import create_agent_node

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "You are helpful.",
                "user": "Do something with {input}",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.return_value = MagicMock(content="Done", tool_calls=[])
            mock_create_llm.return_value = mock_llm

            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={"tools": []},
                tools={},
            )

            node_fn({"input": "test"})

            mock_create_llm.assert_called_once()
            call_kwargs = mock_create_llm.call_args.kwargs

            # This will FAIL - agent ignores model config
            assert (
                call_kwargs.get("model") == "claude-3-5-sonnet-20241022"
            ), f"Agent should use model from YAML. Got: {call_kwargs}"

    def test_agent_uses_temperature_from_prompt_yaml(self) -> None:
        """Agent should use temperature from prompt YAML."""
        from yamlgraph.tools.agent import create_agent_node

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "You are creative.",
                "user": "Generate ideas for {input}",
                "temperature": 0.9,
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.return_value = MagicMock(content="Ideas", tool_calls=[])
            mock_create_llm.return_value = mock_llm

            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={"tools": []},
                tools={},
            )

            node_fn({"input": "test"})

            mock_create_llm.assert_called_once()
            call_kwargs = mock_create_llm.call_args.kwargs

            # This will FAIL - agent ignores temperature
            assert (
                call_kwargs.get("temperature") == 0.9
            ), f"Agent should use temperature from YAML. Got: {call_kwargs}"

    def test_agent_uses_node_config_provider_override(self) -> None:
        """Agent should allow node-level provider override."""
        from yamlgraph.tools.agent import create_agent_node

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "You are helpful.",
                "user": "Do {input}",
                "provider": "anthropic",  # YAML default
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.return_value = MagicMock(content="Done", tool_calls=[])
            mock_create_llm.return_value = mock_llm

            # Node config overrides provider
            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={
                    "tools": [],
                    "provider": "openai",  # Override
                },
                tools={},
            )

            node_fn({"input": "test"})

            mock_create_llm.assert_called_once()
            call_kwargs = mock_create_llm.call_args.kwargs

            # This will FAIL - agent ignores all config
            assert (
                call_kwargs.get("provider") == "openai"
            ), f"Agent should use node config override. Got: {call_kwargs}"


class TestAgentConsistencyWithLLMNodes:
    """Tests that agent nodes behave consistently with LLM nodes."""

    def test_agent_and_llm_nodes_use_same_config_sources(self) -> None:
        """Agent nodes should read config from same sources as LLM nodes.

        LLM nodes read provider/model from:
        1. Node config (highest priority)
        2. Prompt YAML
        3. Environment/defaults

        Agent nodes should follow the same pattern.
        """
        # This is a design requirement test - documents expected behavior
        from yamlgraph.tools.agent import create_agent_node

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "Test",
                "user": "{input}",
                "provider": "mistral",
                "model": "mistral-large-latest",
                "temperature": 0.5,
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.return_value = MagicMock(content="Done", tool_calls=[])
            mock_create_llm.return_value = mock_llm

            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={"tools": []},
                tools={},
            )

            node_fn({"input": "test"})

            # Verify create_llm was called with YAML config
            call_kwargs = mock_create_llm.call_args.kwargs

            # All of these will FAIL
            assert call_kwargs.get("provider") == "mistral"
            assert call_kwargs.get("model") == "mistral-large-latest"
            assert call_kwargs.get("temperature") == 0.5
