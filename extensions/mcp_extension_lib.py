import asyncio
import logging
from typing import Any, Callable, List

import anthropic
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import TextContent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Global constants
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MODEL = "claude-3-7-sonnet-20250219"

PYTHON_TO_JSON_TYPE_MAP = {
    "int": "integer",
    "float": "number",
    "str": "string",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
}


class Server:
    """Manages MCP server connections and tool execution for remote MCP servers."""

    def __init__(self, name: str, mcp_url: str) -> None:
        """
        Initialize a Server instance for a remote MCP server.

        Args:
            name: Name of the server instance
            mcp_url: Direct URL to the remote MCP server
        """
        self.name: str = name
        self.mcp_url: str = mcp_url
        self.session: ClientSession | None = None
        self._streams_context = None
        self._session_context = None

    async def initialize(self) -> None:
        self._streams_context = sse_client(self.mcp_url)
        streams = await self._streams_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()

    async def cleanup(self) -> None:
        """Clean up the server session and streams asynchronously."""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def list_tools(self) -> list[Any]:
        """List available tools from the server.

        Returns:
            A list of available tools.

        Raises:
            RuntimeError: If the server is not initialized.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        tools_response = await self.session.list_tools()
        tools = []

        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                for tool in item[1]:
                    tools.append(Tool(tool.name, tool.description, tool.inputSchema))

        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> Any:
        """Execute a tool with retry mechanism.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            retries: Number of retry attempts.
            delay: Delay between retries in seconds.

        Returns:
            Tool execution result.

        Raises:
            RuntimeError: If server is not initialized.
            Exception: If tool execution fails after all retries.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        attempt = 0
        while attempt < retries:
            try:
                logging.info(f"Executing {tool_name}...")
                result = await self.session.call_tool(tool_name, arguments)

                return result

            except Exception as e:
                attempt += 1
                logging.warning(
                    f"Error executing tool: {e}. Attempt {attempt} of {retries}."
                )
                if attempt < retries:
                    logging.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logging.error("Max retries reached. Failing.")
                    raise


class Tool:
    """Represents a tool with its properties and formatting."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        local_tool: Callable | None = None,
    ) -> None:
        self.name: str = name
        self.description: str = description
        self.input_schema: dict[str, Any] = input_schema
        self.local_tool: Callable | None = local_tool

    def to_dict(self) -> dict:
        """Convert tool to dictionary format for Anthropic client."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @classmethod
    def from_function(cls, func: Callable) -> "Tool":
        input_schema = {}
        input_schema["properties"] = {}
        input_schema["type"] = "object"
        if hasattr(func, "__annotations__"):
            for param_name, param_type in func.__annotations__.items():
                input_schema["properties"][param_name] = {
                    "type": PYTHON_TO_JSON_TYPE_MAP[param_type.__name__],
                    "description": f"The {param_name} parameter",
                }
        return cls(func.__name__, func.__doc__, input_schema, func)


class MCPToolProvider:
    """
    Provides tools from MCP servers and local functions to an Anthropic client.
    """

    def __init__(self):
        self.servers: list[Server] = []
        self.initialized = False
        self.initialization_lock = asyncio.Lock()
        self.additional_tools: list[Tool] = []

    async def __aenter__(self):
        """Enable async context manager usage."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure cleanup when used as context manager."""
        await self.cleanup()
        return False  # Don't suppress exceptions

    async def initialize(
        self,
        mcp_url: str,
        additional_tools: list[Tool] = [],
        server_name: str = "default",
    ) -> None:
        """
        Initialize the MCP tool provider with config.

        Args:
            mcp_url: MCP URL
            additional_tools: Additional tools to include
        """
        try:

            if not mcp_url:
                raise ValueError("MCP URL is required for initialization")

            # Create and initialize server
            server = Server(server_name, mcp_url)
            await server.initialize()
            self.servers = [server]

            self.initialized = True
            logging.info("MCP tool provider initialized successfully")
            self.additional_tools = additional_tools

        except Exception as e:
            logging.error(f"Failed to initialize MCP tool provider: {e}")
            # Ensure cleanup on initialization failure
            await self.cleanup()
            raise

    async def get_all_tools(self) -> list[Tool]:
        """
        Get all available tools from MCP servers and additional tools.

        Args:
            additional_tools: Additional tools to include

        Returns:
            List of all available tools
        """

        additional_tools = self.additional_tools

        if not self.initialized:
            raise RuntimeError("MCP tool provider not initialized")

        all_tools = []

        # Get tools from all servers
        for server in self.servers:
            tools = await server.list_tools()
            all_tools.extend(tools)

        # Add additional tools
        all_tools.extend(additional_tools)

        return all_tools

    async def get_tools_as_dicts(self, additional_tools: list[Tool] = []) -> list[dict]:
        """
        Get all available tools as dictionaries formatted for Anthropic.

        Args:
            additional_tools: Additional tools to include

        Returns:
            List of tool dictionaries
        """
        if not self.initialized:
            raise RuntimeError("MCP tool provider not initialized")

        tools = await self.get_all_tools()
        return [tool.to_dict() for tool in tools]

    async def execute_all_tools(
        self, contents: List[anthropic.types.ContentBlock]
    ) -> str:
        """
        Execute all tools with the given content.
        """
        if not self.initialized:
            raise RuntimeError("MCP tool provider not initialized")

        tool_calls = []
        tool_name = None
        tool_args = None

        for content in contents:
            if isinstance(content, anthropic.types.ToolUseBlock):
                tool_use_id = content.id
                tool_name = content.name
                tool_args = content.input
                tool_calls.append((tool_use_id, tool_name, tool_args))

        tool_results = []

        for tool_use_id, tool_name, tool_args in tool_calls:
            result = await self.execute_tool(tool_name, tool_args)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result,
                }
            )

        return tool_results

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """
        Execute a tool by name with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            additional_tools: Additional tools to check

        Returns:
            Tool execution result
        """

        additional_tools = self.additional_tools
        if not self.initialized:
            raise RuntimeError("MCP tool provider not initialized")

        # First check additional tools
        for tool in additional_tools:
            if tool.name == tool_name and tool.local_tool:
                try:
                    result = tool.local_tool(**arguments)
                    return result
                except Exception as e:
                    error_msg = f"Error executing local tool {tool_name}: {str(e)}"
                    logging.error(error_msg)
                    return error_msg

        # Then check server tools
        for server in self.servers:
            tools = await server.list_tools()
            if any(tool.name == tool_name for tool in tools):
                try:
                    result = await server.execute_tool(tool_name, arguments)

                    if isinstance(result, dict) and "progress" in result:
                        progress = result["progress"]
                        total = result["total"]
                        percentage = (progress / total) * 100
                        logging.info(
                            f"Progress: {progress}/{total} ({percentage:.1f}%)"
                        )

                    if isinstance(result.content[0], TextContent):
                        return result.content[0].text
                    else:
                        return result
                except Exception as e:
                    error_msg = f"Error executing server tool {tool_name}: {str(e)}"
                    logging.error(error_msg)
                    return error_msg

        return f"No tool found with name: {tool_name}"

    def get_tool_calls_summary(
        self, contents: List[anthropic.types.ContentBlock]
    ) -> str:
        tool_calls = []
        for content in contents:
            if isinstance(content, anthropic.types.ToolUseBlock):
                tool_use_id = content.id
                tool_name = content.name
                tool_args = content.input
                tool_calls.append((tool_use_id, tool_name, tool_args))

        # Format tool calls into bullet points
        tool_calls_summary = []
        for tool_use_id, tool_name, tool_args in tool_calls:
            tool_calls_summary.append(f"• {tool_name}: {tool_args}")

        # Join all tool calls into a single string
        tool_calls_text = "Calling tools:\n"
        tool_calls_text += "\n".join(tool_calls_summary)
        logging.info(f"Tool calls executed:\n{tool_calls_text}")
        return tool_calls_text

    async def cleanup(self) -> None:
        """
        Clean up session resources and servers.
        """
        logging.info("Cleaning up MCP tool provider resources")

        # Clean up servers
        for server in self.servers:
            try:
                await server.cleanup()
            except Exception as e:
                logging.error(f"Error while cleaning up server: {e}")

        # Reset state
        self.servers = []
        self.initialized = False
        logging.info("MCP tool provider cleanup completed")
