"""Tests for Python tool nodes (type: python)."""

import pytest

from yamlgraph.tools.python_tool import (
    PythonToolConfig,
    create_python_node,
    load_python_function,
    parse_python_tools,
)


class TestPythonToolConfig:
    """Tests for PythonToolConfig dataclass."""

    @pytest.mark.req("REQ-YG-020")
    def test_basic_config(self):
        """Can create config with required fields."""
        config = PythonToolConfig(
            module="os.path",
            function="join",
        )
        assert config.module == "os.path"
        assert config.function == "join"
        assert config.description == ""

    @pytest.mark.req("REQ-YG-020")
    def test_config_with_description(self):
        """Can create config with description."""
        config = PythonToolConfig(
            module="json",
            function="dumps",
            description="Serialize to JSON",
        )
        assert config.description == "Serialize to JSON"


class TestLoadPythonFunction:
    """Tests for load_python_function."""

    @pytest.mark.req("REQ-YG-020")
    def test_loads_stdlib_function(self):
        """Can load function from stdlib."""
        config = PythonToolConfig(module="os.path", function="join")
        func = load_python_function(config)
        assert callable(func)
        assert func("a", "b") == "a/b"

    @pytest.mark.req("REQ-YG-020")
    def test_loads_json_dumps(self):
        """Can load json.dumps."""
        config = PythonToolConfig(module="json", function="dumps")
        func = load_python_function(config)
        assert func({"a": 1}) == '{"a": 1}'

    @pytest.mark.req("REQ-YG-020")
    def test_raises_on_invalid_module(self):
        """Raises ImportError for non-existent module."""
        config = PythonToolConfig(module="nonexistent.module", function="foo")
        with pytest.raises(ImportError, match="Cannot import module"):
            load_python_function(config)

    @pytest.mark.req("REQ-YG-020")
    def test_raises_on_invalid_function(self):
        """Raises AttributeError for non-existent function."""
        config = PythonToolConfig(module="os.path", function="nonexistent_func")
        with pytest.raises(AttributeError, match="not found in module"):
            load_python_function(config)

    @pytest.mark.req("REQ-YG-020")
    def test_raises_on_non_callable(self):
        """Raises TypeError if attribute is not callable."""
        config = PythonToolConfig(module="os", function="name")
        with pytest.raises(TypeError, match="not callable"):
            load_python_function(config)


class TestParsePythonTools:
    """Tests for parse_python_tools."""

    @pytest.mark.req("REQ-YG-020")
    def test_parses_python_tools(self):
        """Extracts only type: python tools."""
        tools_config = {
            "shell_tool": {"command": "echo hello"},
            "python_tool": {
                "type": "python",
                "module": "json",
                "function": "dumps",
            },
        }
        result = parse_python_tools(tools_config)

        assert len(result) == 1
        assert "python_tool" in result
        assert result["python_tool"].module == "json"
        assert result["python_tool"].function == "dumps"

    @pytest.mark.req("REQ-YG-020")
    def test_skips_shell_tools(self):
        """Does not include shell tools."""
        tools_config = {
            "git_log": {
                "type": "shell",
                "command": "git log",
            },
        }
        result = parse_python_tools(tools_config)
        assert len(result) == 0

    @pytest.mark.req("REQ-YG-020")
    def test_skips_incomplete_python_tools(self):
        """Skips Python tools missing module or function."""
        tools_config = {
            "missing_module": {"type": "python", "function": "foo"},
            "missing_function": {"type": "python", "module": "json"},
        }
        result = parse_python_tools(tools_config)
        assert len(result) == 0

    @pytest.mark.req("REQ-YG-020")
    def test_includes_description(self):
        """Parses description field."""
        tools_config = {
            "my_tool": {
                "type": "python",
                "module": "json",
                "function": "loads",
                "description": "Parse JSON",
            },
        }
        result = parse_python_tools(tools_config)
        assert result["my_tool"].description == "Parse JSON"


class TestCreatePythonNode:
    """Tests for create_python_node."""

    @pytest.mark.req("REQ-YG-020")
    def test_creates_node_function(self):
        """Creates callable node function."""
        python_tools = {
            "my_tool": PythonToolConfig(
                module="tests.unit.test_python_nodes",
                function="sample_node_function",
            ),
        }
        node_config = {"tool": "my_tool", "state_key": "result"}

        node_fn = create_python_node("test_node", node_config, python_tools)
        assert callable(node_fn)

    @pytest.mark.req("REQ-YG-020")
    def test_raises_on_missing_tool(self):
        """Raises if tool not in registry."""
        python_tools = {}
        node_config = {"tool": "nonexistent"}

        with pytest.raises(KeyError, match="not found"):
            create_python_node("test_node", node_config, python_tools)

    @pytest.mark.req("REQ-YG-020")
    def test_raises_on_missing_tool_key(self):
        """Raises if node config missing tool key."""
        python_tools = {}
        node_config = {}

        with pytest.raises(ValueError, match="must specify"):
            create_python_node("test_node", node_config, python_tools)

    @pytest.mark.req("REQ-YG-020")
    def test_node_returns_dict_from_function(self):
        """Node returns function's dict result with current_step."""
        python_tools = {
            "dict_tool": PythonToolConfig(
                module="tests.unit.test_python_nodes",
                function="sample_node_function",
            ),
        }
        node_config = {"tool": "dict_tool"}

        node_fn = create_python_node("test_node", node_config, python_tools)
        result = node_fn({"input": "hello"})

        assert result["current_step"] == "test_node"
        assert "output" in result

    @pytest.mark.req("REQ-YG-020")
    def test_node_wraps_non_dict_return(self):
        """Node wraps non-dict return in state_key."""
        python_tools = {
            "scalar_tool": PythonToolConfig(
                module="tests.unit.test_python_nodes",
                function="scalar_return_function",
            ),
        }
        node_config = {"tool": "scalar_tool", "state_key": "my_value"}

        node_fn = create_python_node("test_node", node_config, python_tools)
        result = node_fn({})

        assert result["my_value"] == 42
        assert result["current_step"] == "test_node"


# Sample functions for testing
def sample_node_function(state: dict) -> dict:
    """Sample node function that returns a dict."""
    return {"output": f"processed: {state.get('input', 'none')}"}


def scalar_return_function(state: dict) -> int:
    """Sample function that returns a scalar."""
    return 42
