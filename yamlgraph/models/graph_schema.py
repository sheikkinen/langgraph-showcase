"""Pydantic schemas for YAML graph configuration validation.

Provides structured validation for graph YAML files with clear error messages.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from yamlgraph.constants import ErrorHandler, NodeType


class SubgraphNodeConfig(BaseModel):
    """Configuration for a subgraph node."""

    type: Literal["subgraph"]
    graph: str = Field(
        ..., description="Path to subgraph YAML file (relative to parent)"
    )
    mode: Literal["invoke", "direct"] = Field(
        default="invoke",
        description="invoke: explicit state mapping; direct: shared schema",
    )
    input_mapping: dict[str, str] | Literal["auto", "*"] = Field(
        default_factory=dict,
        description="Map parent state fields to child input (mode=invoke only)",
    )
    output_mapping: dict[str, str] | Literal["auto", "*"] = Field(
        default_factory=dict,
        description="Map child output fields to parent state (mode=invoke only)",
    )
    interrupt_output_mapping: dict[str, str] | Literal["auto", "*"] = Field(
        default_factory=dict,
        description="Map child state to parent when subgraph interrupts (FR-006)",
    )
    checkpointer: str | None = Field(
        default=None,
        description="Override parent checkpointer",
    )

    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_config(self) -> "SubgraphNodeConfig":
        """Validate subgraph configuration."""
        if not self.graph.endswith((".yaml", ".yml")):
            raise ValueError(f"Subgraph must be a YAML file: {self.graph}")
        if self.mode == "direct" and (self.input_mapping or self.output_mapping):
            raise ValueError("mode=direct does not support input/output mappings")
        return self


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
    loop_limits: dict[str, int] = Field(default_factory=dict)
    data_files: dict[str, str] = Field(
        default_factory=dict,
        description="External YAML data files to load into state at compile time",
    )

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


def export_graph_json_schema() -> dict[str, Any]:
    """Export graph configuration as JSON Schema for IDE support.

    Returns a JSON Schema dict compatible with VS Code YAML extension
    and other JSON Schema validators.

    Returns:
        JSON Schema dict with $schema, $id, and full type definitions
    """
    schema = GraphConfigSchema.model_json_schema()

    # Add JSON Schema metadata
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["$id"] = "https://yamlgraph.dev/schemas/graph-v1.json"
    schema["title"] = "YamlGraph Graph Configuration"
    schema["description"] = "Schema for YamlGraph graph.yaml files"

    return schema
