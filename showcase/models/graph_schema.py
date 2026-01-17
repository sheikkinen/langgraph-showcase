"""Pydantic schemas for YAML graph configuration validation.

Provides structured validation for graph YAML files with clear error messages.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from showcase.constants import ErrorHandler, NodeType


class NodeConfig(BaseModel):
    """Configuration for a single graph node."""

    type: str = Field(default=NodeType.LLM, description="Node type")
    prompt: str | None = Field(default=None, description="Prompt template name")
    state_key: str | None = Field(default=None, description="State key for output")
    temperature: float | None = Field(default=None, ge=0, le=2)
    provider: str | None = Field(default=None)
    on_error: str | None = Field(default=None)
    fallback: dict[str, Any] | None = Field(default=None)
    variables: dict[str, str] = Field(default_factory=dict)
    requires: list[str] = Field(default_factory=list)
    routes: dict[str, str] | None = Field(default=None, description="Router routes")

    # Map node fields
    over: str | None = Field(default=None, description="Map over expression")
    # 'as' is reserved in Python, handled specially
    item_var: str | None = Field(default=None, alias="as")
    node: dict[str, Any] | None = Field(default=None, description="Map sub-node")
    collect: str | None = Field(default=None, description="Map collect key")

    # Tool/Agent fields
    tools: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=10, ge=1)

    model_config = {"extra": "allow", "populate_by_name": True}

    @field_validator("on_error")
    @classmethod
    def validate_on_error(cls, v: str | None) -> str | None:
        """Validate on_error is a known handler."""
        if v is not None and v not in ErrorHandler.all_values():
            valid = ", ".join(ErrorHandler.all_values())
            raise ValueError(f"Invalid on_error '{v}'. Valid: {valid}")
        return v

    @model_validator(mode="after")
    def validate_node_requirements(self) -> "NodeConfig":
        """Validate node has required fields based on type."""
        if NodeType.requires_prompt(self.type) and not self.prompt:
            raise ValueError(f"Node type '{self.type}' requires 'prompt' field")

        if self.type == NodeType.ROUTER and not self.routes:
            raise ValueError("Router node requires 'routes' field")

        if self.type == NodeType.MAP:
            if not self.over:
                raise ValueError("Map node requires 'over' field")
            if not self.item_var:
                raise ValueError("Map node requires 'as' field")
            if not self.node:
                raise ValueError("Map node requires 'node' field")
            if not self.collect:
                raise ValueError("Map node requires 'collect' field")

        return self


class EdgeConfig(BaseModel):
    """Configuration for a graph edge."""

    from_node: str = Field(..., alias="from", description="Source node")
    to: str | list[str] = Field(..., description="Target node(s)")
    condition: str | None = Field(default=None, description="Condition expression")

    model_config = {"populate_by_name": True}


class GraphConfigSchema(BaseModel):
    """Full YAML graph configuration schema.

    Use this for validating graph YAML files with Pydantic.
    """

    version: str = Field(default="1.0")
    name: str = Field(default="unnamed")
    description: str = Field(default="")
    defaults: dict[str, Any] = Field(default_factory=dict)
    nodes: dict[str, NodeConfig] = Field(...)
    edges: list[EdgeConfig] = Field(...)
    tools: dict[str, Any] = Field(default_factory=dict)
    state_class: str = Field(default="")
    loop_limits: dict[str, int] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_router_targets(self) -> "GraphConfigSchema":
        """Validate router routes point to existing nodes."""
        for node_name, node in self.nodes.items():
            if node.type == NodeType.ROUTER and node.routes:
                for route_key, target in node.routes.items():
                    if target not in self.nodes:
                        raise ValueError(
                            f"Router '{node_name}' route '{route_key}' "
                            f"targets nonexistent node '{target}'"
                        )
        return self

    @model_validator(mode="after")
    def validate_edge_nodes(self) -> "GraphConfigSchema":
        """Validate edge sources and targets exist."""
        valid_nodes = set(self.nodes.keys()) | {"START", "END"}

        for edge in self.edges:
            if edge.from_node not in valid_nodes:
                raise ValueError(f"Edge 'from' node '{edge.from_node}' not found")

            targets = edge.to if isinstance(edge.to, list) else [edge.to]
            for target in targets:
                if target not in valid_nodes:
                    raise ValueError(f"Edge 'to' node '{target}' not found")

        return self


def validate_graph_schema(config: dict[str, Any]) -> GraphConfigSchema:
    """Validate a graph configuration dict using Pydantic.

    Args:
        config: Raw parsed YAML configuration

    Returns:
        Validated GraphConfigSchema

    Raises:
        pydantic.ValidationError: If validation fails
    """
    return GraphConfigSchema.model_validate(config)
