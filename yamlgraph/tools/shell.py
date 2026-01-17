"""Shell tool executor for running commands with variable substitution.

This module provides the core shell tool execution functionality,
allowing YAML-defined tools to run shell commands with parsed output.

Security Model:
    Variables are sanitized with shlex.quote() to prevent shell injection.
    The command template itself is trusted (from YAML config), but all
    user-provided variable values are escaped before substitution.

    Example:
        command: "git log --author={author}"
        variables: {"author": "$(rm -rf /)"}
        → Executed: git log --author='$(rm -rf /)'  (safely quoted)
"""

from __future__ import annotations

import json
import logging
import os
import shlex
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


def sanitize_variables(variables: dict[str, Any]) -> dict[str, str]:
    """Sanitize variable values for safe shell substitution.

    Uses shlex.quote() to escape values, preventing shell injection.

    Args:
        variables: Raw variable values

    Returns:
        Sanitized variables safe for shell interpolation
    """
    sanitized = {}
    for key, value in variables.items():
        if value is None:
            sanitized[key] = ""
        elif isinstance(value, (list, dict)):
            # Convert complex types to JSON, then quote
            sanitized[key] = shlex.quote(json.dumps(value))
        else:
            sanitized[key] = shlex.quote(str(value))
    return sanitized


def execute_shell_tool(
    config: ShellToolConfig,
    variables: dict[str, Any],
    sanitize: bool = True,
) -> ToolResult:
    """Execute shell command with variable substitution.

    Args:
        config: Tool configuration with command template
        variables: Values to substitute into command placeholders
        sanitize: Whether to sanitize variables with shlex.quote (default True)

    Returns:
        ToolResult with success status and parsed output or error
    """
    # Sanitize variables to prevent shell injection
    safe_vars = sanitize_variables(variables) if sanitize else variables

    # Substitute variables into command
    try:
        command = config.command.format(**safe_vars)
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
        # Security: shell=True is required for command templates with pipes/redirects.
        # All user-provided variables are sanitized via shlex.quote() in sanitize_variables()
        # before substitution, preventing shell injection attacks. The command template
        # itself comes from trusted YAML configuration, not user input.
        result = subprocess.run(
            command,
            shell=True,  # nosec B602
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

    Only parses shell tools (type: shell or no type specified with command).
    Skips Python tools (type: python).

    Args:
        tools_config: Dict from YAML tools: section

    Returns:
        Registry mapping tool names to ShellToolConfig objects
    """
    registry: dict[str, ShellToolConfig] = {}

    for name, config in tools_config.items():
        # Skip Python tools
        if config.get("type") == "python":
            continue
        # Skip tools without command (invalid shell tools)
        if "command" not in config:
            continue

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
