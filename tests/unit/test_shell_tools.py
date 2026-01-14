"""Tests for shell tool executor."""



from showcase.tools.shell import (
    ShellToolConfig,
    execute_shell_tool,
    parse_tools,
)


class TestShellToolConfig:
    """Tests for ShellToolConfig dataclass."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = ShellToolConfig(command="echo hello")
        assert config.command == "echo hello"
        assert config.description == ""
        assert config.parse == "text"
        assert config.timeout == 30
        assert config.working_dir == "."
        assert config.env == {}
        assert config.success_codes == [0]

    def test_custom_values(self):
        """Config accepts custom values."""
        config = ShellToolConfig(
            command="curl http://api.example.com",
            description="Fetch API data",
            parse="json",
            timeout=60,
            working_dir="/tmp",
            env={"API_KEY": "secret"},
            success_codes=[0, 1],
        )
        assert config.parse == "json"
        assert config.timeout == 60
        assert config.env == {"API_KEY": "secret"}


class TestExecuteShellTool:
    """Tests for execute_shell_tool function."""

    def test_executes_command(self):
        """Simple command executes successfully."""
        config = ShellToolConfig(command="echo hello")
        result = execute_shell_tool(config, {})
        assert result.success is True
        assert result.output.strip() == "hello"
        assert result.error is None

    def test_substitutes_variables(self):
        """Placeholders replaced with values."""
        config = ShellToolConfig(command="echo {message}")
        result = execute_shell_tool(config, {"message": "world"})
        assert result.success is True
        assert result.output.strip() == "world"

    def test_multiple_variables(self):
        """Multiple placeholders all substituted."""
        config = ShellToolConfig(command="echo {a} {b} {c}")
        result = execute_shell_tool(config, {"a": "1", "b": "2", "c": "3"})
        assert result.output.strip() == "1 2 3"

    def test_parses_json_output(self):
        """JSON stdout parsed to dict."""
        # Double braces escape them from .format()
        config = ShellToolConfig(
            command="echo '{{\"name\": \"test\", \"value\": 42}}'",
            parse="json",
        )
        result = execute_shell_tool(config, {})
        assert result.success is True
        assert result.output == {"name": "test", "value": 42}

    def test_parse_none_returns_none(self):
        """parse=none returns None for side-effect commands."""
        config = ShellToolConfig(command="echo ignored", parse="none")
        result = execute_shell_tool(config, {})
        assert result.success is True
        assert result.output is None

    def test_handles_timeout(self):
        """Long-running command times out."""
        config = ShellToolConfig(command="sleep 10", timeout=1)
        result = execute_shell_tool(config, {})
        assert result.success is False
        assert "timed out" in result.error.lower()

    def test_captures_stderr_on_error(self):
        """Non-zero exit captures stderr."""
        config = ShellToolConfig(command="ls /nonexistent_path_xyz")
        result = execute_shell_tool(config, {})
        assert result.success is False
        assert result.error is not None
        assert "No such file" in result.error or "nonexistent" in result.error.lower()

    def test_custom_success_codes(self):
        """Custom success codes treated as success."""
        # grep returns 1 when no match found
        config = ShellToolConfig(
            command="grep nonexistent /dev/null",
            success_codes=[0, 1],
        )
        result = execute_shell_tool(config, {})
        assert result.success is True

    def test_working_dir(self):
        """Command runs in specified directory."""
        config = ShellToolConfig(command="pwd", working_dir="/tmp")
        result = execute_shell_tool(config, {})
        assert result.success is True
        assert "/tmp" in result.output

    def test_env_variables(self):
        """Environment variables passed to command."""
        config = ShellToolConfig(
            command="echo $TEST_VAR",
            env={"TEST_VAR": "secret_value"},
        )
        result = execute_shell_tool(config, {})
        assert result.success is True
        assert "secret_value" in result.output

    def test_invalid_json_parse_fails(self):
        """Invalid JSON returns error."""
        config = ShellToolConfig(command="echo 'not json'", parse="json")
        result = execute_shell_tool(config, {})
        assert result.success is False
        assert "json" in result.error.lower()


class TestParseTools:
    """Tests for parse_tools function."""

    def test_empty_config(self):
        """Empty config returns empty registry."""
        registry = parse_tools({})
        assert registry == {}

    def test_parses_single_tool(self):
        """Single tool parsed correctly."""
        config = {
            "search": {
                "command": "curl -s {url}",
                "description": "Search the web",
                "parse": "json",
                "timeout": 60,
            }
        }
        registry = parse_tools(config)
        assert "search" in registry
        assert registry["search"].command == "curl -s {url}"
        assert registry["search"].description == "Search the web"
        assert registry["search"].parse == "json"
        assert registry["search"].timeout == 60

    def test_parses_multiple_tools(self):
        """Multiple tools all parsed."""
        config = {
            "tool1": {"command": "echo 1"},
            "tool2": {"command": "echo 2"},
            "tool3": {"command": "echo 3"},
        }
        registry = parse_tools(config)
        assert len(registry) == 3
        assert all(name in registry for name in ["tool1", "tool2", "tool3"])

    def test_default_values_applied(self):
        """Missing optional fields get defaults."""
        config = {"minimal": {"command": "echo hello"}}
        registry = parse_tools(config)
        tool = registry["minimal"]
        assert tool.description == ""
        assert tool.parse == "text"
        assert tool.timeout == 30
        assert tool.working_dir == "."
        assert tool.env == {}

    def test_parses_env_and_working_dir(self):
        """env and working_dir parsed correctly."""
        config = {
            "script": {
                "command": "node index.js",
                "working_dir": "./scripts",
                "env": {"NODE_ENV": "production"},
            }
        }
        registry = parse_tools(config)
        assert registry["script"].working_dir == "./scripts"
        assert registry["script"].env == {"NODE_ENV": "production"}
