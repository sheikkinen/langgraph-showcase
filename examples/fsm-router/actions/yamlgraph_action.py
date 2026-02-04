"""
YAMLGraph Action - Run a YAMLGraph pipeline as an FSM action.

This is a statemachine-engine custom action that executes a YAMLGraph
pipeline and returns an event based on the result.

YAML Usage:
    actions:
      - type: yamlgraph
        params:
          graph: graphs/classifier.yaml
          input_key: query        # Context key to pass as input
          output_key: result      # Context key to store result
          success: classified     # Event on success
          failure: classify_failed
"""

import logging
from pathlib import Path
from typing import Any

from statemachine_engine.actions.base import BaseAction

logger = logging.getLogger(__name__)


class YamlgraphAction(BaseAction):
    """Execute a YAMLGraph pipeline as an FSM action."""

    async def execute(self, context: dict[str, Any]) -> str:
        """
        Execute the YAMLGraph pipeline.

        Args:
            context: FSM execution context containing input data

        Returns:
            Event name to trigger next transition
        """
        params = self.config.get("params", {})
        graph_path = params.get("graph")
        input_key = params.get("input_key", "input")
        output_key = params.get("output_key", "yamlgraph_result")
        success_event = params.get("success", "completed")
        failure_event = params.get("failure", "failed")

        if not graph_path:
            logger.error("No graph path specified in yamlgraph action")
            context["error"] = "No graph path specified"
            return failure_event

        # Resolve graph path relative to action file or config
        action_dir = Path(__file__).parent.parent
        resolved_path = action_dir / graph_path
        if not resolved_path.exists():
            resolved_path = Path(graph_path)

        try:
            # Import YAMLGraph at runtime to avoid hard dependency
            from yamlgraph.executor_async import (
                load_and_compile_async,
                run_graph_async,
            )

            logger.info(f"📊 Loading YAMLGraph: {resolved_path}")
            app = await load_and_compile_async(str(resolved_path))

            # Build initial state from context
            initial_state = {input_key: context.get(input_key, "")}

            # Add any extra variables from params
            variables = params.get("variables", {})
            for key, value in variables.items():
                # Interpolate {context_key} references
                if (
                    isinstance(value, str)
                    and value.startswith("{")
                    and value.endswith("}")
                ):
                    ctx_key = value[1:-1]
                    initial_state[key] = context.get(ctx_key, value)
                else:
                    initial_state[key] = value

            logger.info(f"🚀 Running YAMLGraph with: {list(initial_state.keys())}")
            result = await run_graph_async(app, initial_state)

            # Store result in context for downstream actions
            context[output_key] = result
            logger.info(f"✅ YAMLGraph completed, stored result in '{output_key}'")

            # Check for routing decision if present
            # Look in top-level result and in nested objects (e.g., classification.route)
            route_event = None
            if "route" in result:
                route_event = result.get("route")
            else:
                # Search nested dicts for route field
                for _key, value in result.items():
                    if isinstance(value, dict) and "route" in value:
                        route_event = value.get("route")
                        break

            if route_event:
                logger.info(f"🔀 YAMLGraph returned route: {route_event}")
                return route_event

            return success_event

        except ImportError as e:
            logger.error(f"YAMLGraph not installed: {e}")
            context["error"] = "YAMLGraph not installed. Run: pip install -e '.[fsm]'"
            return failure_event

        except Exception as e:
            logger.error(f"YAMLGraph execution failed: {e}")
            context["error"] = str(e)
            return failure_event
