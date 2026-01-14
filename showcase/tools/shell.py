"""Shell tool executor for running commands with variable substitution.

This module provides the core shell tool execution functionality,
allowing YAML-defined tools to run shell commands with parsed output.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ShellToolConfig:
    """Configuration for a shell tool.
    
    Attributes:
        command: Shell command with {variable} placeholders
        description: Human-readable description for LLM tool selection
        parse: Output parsing mode - 'text', 'json', or 'none'
        timeout: Max seconds before command is killed
        working_dir: Directory to run command in
        env: Additional environment variables
        success_codes: Exit codes considered successful
    """

    command: str
    description: str = ""
    parse: str = "text"  # text | json | none
    timeout: int = 30
    working_dir: str = "."
    env: dict[str, str] = field(default_factory=dict)
    success_codes: list[int] = field(default_factory=lambda: [0])


@dataclass
class ToolResult:
    """Result from executing a shell tool.
    
    Attributes:
        success: Whether the command succeeded
        output: Parsed output (str, dict, or None based on parse mode)
        error: Error message if failed
    """

    success: bool
    output: Any = None
    error: str | None = None


def execute_shell_tool(
    config: ShellToolConfig,
    variables: dict[str, Any],
) -> ToolResult:
    """Execute shell command with variable substitution.
    
    Args:
        config: Tool configuration with command template
        variables: Values to substitute into command placeholders
        
    Returns:
        ToolResult with success status and parsed output or error
    """
    # Substitute variables into command
    try:
        command = config.command.format(**variables)
    except KeyError as e:
        return ToolResult(
            success=False,
            error=f"Missing variable: {e}",
        )

    logger.debug(f"Executing: {command}")

    # Build environment
    env = os.environ.copy()
    env.update(config.env)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=config.timeout,
            cwd=config.working_dir,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            success=False,
            error=f"Command timed out after {config.timeout} seconds",
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Execution error: {e}",
        )

    # Check exit code
    if result.returncode not in config.success_codes:
        return ToolResult(
            success=False,
            output=result.stdout,
            error=result.stderr or f"Exit code {result.returncode}",
        )

    # Parse output
    output = result.stdout
    if config.parse == "json":
        try:
            output = json.loads(output)
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                error=f"JSON parse error: {e}",
            )
    elif config.parse == "none":
        output = None

    return ToolResult(success=True, output=output)


def parse_tools(tools_config: dict[str, Any]) -> dict[str, ShellToolConfig]:
    """Parse tools: section from YAML into ShellToolConfig registry.
    
    Args:
        tools_config: Dict from YAML tools: section
        
    Returns:
        Registry mapping tool names to ShellToolConfig objects
    """
    registry: dict[str, ShellToolConfig] = {}

    for name, config in tools_config.items():
        registry[name] = ShellToolConfig(
            command=config["command"],
            description=config.get("description", ""),
            parse=config.get("parse", "text"),
            timeout=config.get("timeout", 30),
            working_dir=config.get("working_dir", "."),
            env=config.get("env", {}),
            success_codes=config.get("success_codes", [0]),
        )

    return registry
