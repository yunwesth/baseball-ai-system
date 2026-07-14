"""
MCP client for the Baseball AI orchestrator.

This module starts the local MCP server as a subprocess and communicates
with it through the MCP stdio transport.
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, ListToolsResult

from config import (
    BASEBALL_API_URL,
    MCP_SERVER_PATH,
)


class MCPClient:
    """
    Client used by the orchestrator to communicate with the MCP server.
    """

    def __init__(self) -> None:
        """
        Prepare the MCP server subprocess configuration.

        The MCP server is not started until session() is entered.
        """
        server_path = Path(MCP_SERVER_PATH).resolve()

        if not server_path.is_file():
            raise FileNotFoundError(
                f"MCP server file was not found: {server_path}"
            )

        # Start with a copy of the current process environment.
        child_environment = os.environ.copy()

        # Explicitly pass the Baseball API URL to the MCP server subprocess.
        # This value comes from config.py, which loads orchestrator/.env.
        child_environment["BASEBALL_API_URL"] = BASEBALL_API_URL

        self._server_parameters = StdioServerParameters(
            # Use the exact same Python interpreter and virtual environment
            # that are running the orchestrator.
            command=sys.executable,
            args=[str(server_path)],
            env=child_environment,
        )

        self._session: ClientSession | None = None

    @property
    def connected(self) -> bool:
        """
        Return True when an initialized MCP session is active.
        """
        return self._session is not None

    def _require_session(self) -> ClientSession:
        """
        Return the active MCP session.

        Raise a clear error if an MCP operation is attempted before
        entering session().
        """
        if self._session is None:
            raise RuntimeError(
                "MCP Client is not connected. "
                "Use 'async with client.session():' first."
            )

        return self._session

    @asynccontextmanager
    async def session(self) -> AsyncIterator[None]:
        """
        Start the MCP server, open a session, and initialize it.

        The subprocess and streams are automatically closed when the
        context manager exits.
        """
        if self.connected:
            raise RuntimeError(
                "MCP Client already has an active session."
            )

        async with stdio_client(
            self._server_parameters
        ) as (read_stream, write_stream):

            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:

                self._session = session

                try:
                    await session.initialize()
                    yield
                finally:
                    self._session = None

    async def list_tools(self) -> ListToolsResult:
        """
        Return the tools exposed by the MCP server.
        """
        session = self._require_session()

        return await session.list_tools()

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> CallToolResult:
        """
        Call one MCP tool with the supplied arguments.
        """
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ValueError(
                "tool_name must be a non-empty string."
            )

        if arguments is not None and not isinstance(arguments, dict):
            raise ValueError(
                "arguments must be a dictionary or None."
            )

        session = self._require_session()

        return await session.call_tool(
            tool_name.strip(),
            arguments=arguments or {},
        )
