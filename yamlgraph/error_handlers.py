"""Error handling strategies for node execution.

Provides strategy functions for different error handling modes:
- skip: Continue without output
- fail: Raise exception immediately
- retry: Retry up to N times
- fallback: Try fallback provider
"""

import logging
from typing import Any, Callable

from yamlgraph.models import ErrorType, PipelineError

logger = logging.getLogger(__name__)


class NodeResult:
    """Result of node execution with consistent structure.

    Attributes:
        success: Whether execution succeeded
        output: The result value (if success)
        error: PipelineError (if failure)
        state_updates: Additional state updates
    """

    def __init__(
        self,
        success: bool,
        output: Any = None,
        error: PipelineError | None = None,
        state_updates: dict | None = None,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.state_updates = state_updates or {}

    def to_state_update(
        self,
        state_key: str,
        node_name: str,
        loop_counts: dict,
    ) -> dict:
        """Convert to LangGraph state update dict.

        Args:
            state_key: Key to store output under
            node_name: Name of the node
            loop_counts: Current loop counts

        Returns:
            State update dict with consistent structure
        """
        update = {
            "current_step": node_name,
            "_loop_counts": loop_counts,
        }

        if self.success:
            update[state_key] = self.output
        elif self.error:
            # Always use 'errors' list for consistency
            update["errors"] = [self.error]

        update.update(self.state_updates)
        return update


def handle_skip(
    node_name: str,
    error: Exception,
    loop_counts: dict,
) -> NodeResult:
    """Handle error with skip strategy.

    Args:
        node_name: Name of the node
        error: The exception that occurred
        loop_counts: Current loop counts

    Returns:
        NodeResult with empty output
    """
    logger.warning(f"Node {node_name} failed, skipping: {error}")
    return NodeResult(success=True, output=None)


def handle_fail(
    node_name: str,
    error: Exception,
) -> None:
    """Handle error with fail strategy.

    Args:
        node_name: Name of the node
        error: The exception that occurred

    Raises:
        Exception: Always raises the original error
    """
    logger.error(f"Node {node_name} failed (on_error=fail): {error}")
    raise error


def handle_retry(
    node_name: str,
    execute_fn: Callable[[], tuple[Any, Exception | None]],
    max_retries: int,
) -> NodeResult:
    """Handle error with retry strategy.

    Args:
        node_name: Name of the node
        execute_fn: Function to execute (returns result, error)
        max_retries: Maximum retry attempts

    Returns:
        NodeResult with output or error
    """
    last_exception: Exception | None = None

    for attempt in range(1, max_retries + 1):
        logger.info(f"Node {node_name} retry {attempt}/{max_retries}")
        result, error = execute_fn()
        if error is None:
            return NodeResult(success=True, output=result)
        last_exception = error

    logger.error(f"Node {node_name} failed after {max_retries} attempts")
    pipeline_error = PipelineError.from_exception(
        last_exception or Exception("Unknown error"), node=node_name
    )
    return NodeResult(success=False, error=pipeline_error)


def handle_fallback(
    node_name: str,
    execute_fn: Callable[[str | None], tuple[Any, Exception | None]],
    fallback_provider: str,
) -> NodeResult:
    """Handle error with fallback strategy.

    Args:
        node_name: Name of the node
        execute_fn: Function to execute with provider param
        fallback_provider: Fallback provider to try

    Returns:
        NodeResult with output or error
    """
    logger.info(f"Node {node_name} trying fallback: {fallback_provider}")
    result, fallback_error = execute_fn(fallback_provider)

    if fallback_error is None:
        return NodeResult(success=True, output=result)

    logger.error(f"Node {node_name} failed with primary and fallback")
    pipeline_error = PipelineError.from_exception(fallback_error, node=node_name)
    return NodeResult(success=False, error=pipeline_error)


def handle_default(
    node_name: str,
    error: Exception,
) -> NodeResult:
    """Handle error with default strategy (log and return error).

    Args:
        node_name: Name of the node
        error: The exception that occurred

    Returns:
        NodeResult with error
    """
    logger.error(f"Node {node_name} failed: {error}")
    pipeline_error = PipelineError.from_exception(error, node=node_name)
    return NodeResult(success=False, error=pipeline_error)


def check_requirements(
    requires: list[str],
    state: dict,
    node_name: str,
) -> PipelineError | None:
    """Check if all required state keys are present.

    Args:
        requires: List of required state keys
        state: Current state
        node_name: Name of the node

    Returns:
        PipelineError if requirements not met, None otherwise
    """
    for req in requires:
        if state.get(req) is None:
            return PipelineError(
                type=ErrorType.STATE_ERROR,
                message=f"Missing required state: {req}",
                node=node_name,
                retryable=False,
            )
    return None


def check_loop_limit(
    node_name: str,
    loop_limit: int | None,
    current_count: int,
) -> bool:
    """Check if loop limit has been reached.

    Args:
        node_name: Name of the node
        loop_limit: Maximum loop iterations (None = no limit)
        current_count: Current iteration count

    Returns:
        True if limit reached, False otherwise
    """
    if loop_limit is not None and current_count >= loop_limit:
        logger.warning(f"Node {node_name} hit loop limit ({loop_limit})")
        return True
    return False
