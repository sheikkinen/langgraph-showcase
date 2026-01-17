"""Deprecation utilities for CLI commands.

Provides DeprecationError exception and helpers for migrating
old commands to the universal graph runner.

Term 'backward compatibility' signals refactoring need per project guidelines.

Example:
    >>> from yamlgraph.cli.deprecation import DeprecationError, deprecated_command
    >>>
    >>> def cmd_old_command(args):
    ...     # Signal this command needs refactoring
    ...     deprecated_command("old", "graph run graphs/new.yaml --var x=y")
    ...
    >>> # Running raises:
    >>> # DeprecationError: DEPRECATED: 'old' is deprecated.
    >>> # Use 'graph run graphs/new.yaml --var x=y' instead.
"""


class DeprecationError(Exception):
    """Raised when a deprecated command is used.

    Signals "Refactor me" - deprecated commands should be removed.

    Attributes:
        old_command: The deprecated command being used
        new_command: The replacement command to use instead
    """

    def __init__(self, old_command: str, new_command: str):
        self.old_command = old_command
        self.new_command = new_command
        message = (
            f"DEPRECATED: '{old_command}' is deprecated. Use '{new_command}' instead."
        )
        super().__init__(message)


# Command mappings: old command -> graph path
COMMAND_MAPPINGS = {
    "route": "graphs/router-demo.yaml",
    "refine": "graphs/reflexion-demo.yaml",
    "git-report": "graphs/git-report.yaml",
    "memory-demo": "graphs/memory-demo.yaml",
}

# Variable mappings: old command -> arg name -> var name
ARG_MAPPINGS = {
    "route": {"message": "message"},
    "refine": {"topic": "topic"},
    "git-report": {"query": "input"},
    "memory-demo": {"input": "input"},
}


def get_replacement_command(old_command: str, args: dict[str, str]) -> str | None:
    """Get the replacement graph run command.

    Args:
        old_command: The deprecated command name
        args: Dict of argument values

    Returns:
        Replacement command string, or None if unknown command
    """
    graph_path = COMMAND_MAPPINGS.get(old_command)
    if not graph_path:
        return None

    # Build --var arguments
    var_args = []
    arg_mapping = ARG_MAPPINGS.get(old_command, {})
    for arg_name, var_name in arg_mapping.items():
        if arg_name in args:
            var_args.append(f"--var {var_name}={args[arg_name]}")

    var_str = " ".join(var_args)
    return f"graph run {graph_path} {var_str}".strip()


def deprecated_command(old_command: str, new_command: str) -> None:
    """Raise DeprecationError for a deprecated command.

    Args:
        old_command: The deprecated command being used
        new_command: The replacement command suggestion

    Raises:
        DeprecationError: Always raised to signal deprecation
    """
    raise DeprecationError(old_command, new_command)
