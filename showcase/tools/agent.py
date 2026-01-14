"""Agent node factory for LLM-driven tool loops.

This module provides the agent node type that allows the LLM to
autonomously decide which tools to call until it has enough
information to provide a final answer.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from showcase.models.state import ShowcaseState
from showcase.tools.shell import ShellToolConfig, execute_shell_tool
from showcase.utils.llm_factory import create_llm

logger = logging.getLogger(__name__)


def build_langchain_tool(name: str, config: ShellToolConfig) -> Callable:
    """Convert shell config to LangChain Tool.
    
    Args:
        name: Tool name for LLM to reference
        config: Shell tool configuration
        
    Returns:
        LangChain-compatible tool function
    """
    import re
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field, create_model
    
    # Extract variable names from command template
    var_names = re.findall(r'\{(\w+)\}', config.command)
    
    # Create dynamic Pydantic model for tool args
    if var_names:
        fields = {var: (str, Field(description=f"Value for {var}")) for var in var_names}
        ArgsModel = create_model(f"{name}_args", **fields)
    else:
        ArgsModel = None
    
    def execute_tool_with_dict(**kwargs) -> str:
        """Execute shell command with provided arguments."""
        result = execute_shell_tool(config, kwargs)
        if result.success:
            return str(result.output).strip() if result.output is not None else "Success"
        else:
            return f"Error: {result.error}"
    
    return StructuredTool.from_function(
        func=execute_tool_with_dict,
        name=name,
        description=config.description,
        args_schema=ArgsModel,
    )


def _load_prompt(prompt_name: str) -> tuple[str, str]:
    """Load system and user prompts from YAML file.
    
    Args:
        prompt_name: Name of prompt file (without .yaml)
        
    Returns:
        Tuple of (system_prompt, user_template)
    """
    prompt_path = Path("prompts") / f"{prompt_name}.yaml"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path) as f:
        prompt_config = yaml.safe_load(f)

    return prompt_config.get("system", ""), prompt_config.get("user", "{input}")


def create_agent_node(
    node_name: str,
    node_config: dict[str, Any],
    tools: dict[str, ShellToolConfig],
) -> Callable[[ShowcaseState], dict]:
    """Create an agent node that loops with tool calls.
    
    The agent will:
    1. Send the prompt to the LLM with available tools
    2. If LLM returns tool calls, execute them and feed results back
    3. Repeat until LLM returns without tool calls or max_iterations reached
    
    Args:
        node_name: Name of the node in the graph
        node_config: Node configuration from YAML
        tools: Registry of available tools
        
    Returns:
        Node function that runs the agent loop
    """
    tool_names = node_config.get("tools", [])
    max_iterations = node_config.get("max_iterations", 5)
    state_key = node_config.get("state_key", node_name)
    prompt_name = node_config.get("prompt", "agent")

    # Build LangChain tools from shell configs
    lc_tools = [build_langchain_tool(name, tools[name]) for name in tool_names]
    tool_lookup = {name: tools[name] for name in tool_names}

    def node_fn(state: ShowcaseState) -> dict:
        """Execute the agent loop."""
        # Load prompts
        try:
            system_prompt, user_template = _load_prompt(prompt_name)
        except FileNotFoundError:
            # Fallback for testing
            system_prompt = "You are a helpful assistant with access to tools."
            user_template = "{input}"

        # Format user prompt with state - handle missing keys
        import re
        def replace_var(match):
            key = match.group(1)
            return str(state.get(key, f"{{{key}}}"))
        
        user_prompt = re.sub(r'\{(\w+)\}', replace_var, user_template)

        # Initialize messages
        messages: list = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Get LLM with tools bound
        llm = create_llm().bind_tools(lc_tools)

        logger.info(f"🤖 Starting agent loop: {node_name} (max {max_iterations} iterations)")
        logger.debug(f"Tools available: {[t.name for t in lc_tools]}")
        logger.debug(f"User prompt: {user_prompt[:100]}...")

        for iteration in range(max_iterations):
            logger.debug(f"Agent iteration {iteration + 1}/{max_iterations}")

            # Get LLM response
            response = llm.invoke(messages)
            messages.append(response)
            
            logger.debug(f"Response tool_calls: {response.tool_calls}")

            # Check if LLM wants to call tools
            if not response.tool_calls:
                # Done - LLM finished reasoning
                logger.info(f"✓ Agent completed after {iteration + 1} iterations")
                return {
                    state_key: response.content,
                    "current_step": node_name,
                    "_agent_iterations": iteration + 1,
                }

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call.get("id", f"call_{iteration}")

                logger.info(f"🔧 Calling tool: {tool_name}({tool_args})")

                # Execute the tool
                tool_config = tool_lookup.get(tool_name)
                if tool_config:
                    result = execute_shell_tool(tool_config, tool_args)
                    output = str(result.output) if result.success else f"Error: {result.error}"
                else:
                    output = f"Error: Unknown tool '{tool_name}'"

                # Add tool result to messages
                messages.append(
                    ToolMessage(content=output, tool_call_id=tool_id)
                )

        # Hit max iterations
        logger.warning(f"Agent hit max iterations ({max_iterations})")
        last_content = messages[-1].content if hasattr(messages[-1], "content") else ""
        return {
            state_key: last_content,
            "current_step": node_name,
            "_agent_iterations": max_iterations,
            "_agent_limit_reached": True,
        }

    return node_fn
