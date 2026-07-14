"""
mcp_client.py

MCP 서버와의 연결, 초기화, 도구 조회 및 도구 호출을 담당한다.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, ListToolsResult

from config import MCP_SERVER_PATH, PYTHON_COMMAND


class MCPClient:
    """
    stdio transport를 사용하여 MCP 서버와 통신하는 클라이언트.
    """

    def __init__(self) -> None:
        """
        MCP 서버 실행 정보를 준비한다.

        이 시점에는 아직 서버가 실행되거나 연결되지 않는다.
        """
        import os

        self._server_parameters = StdioServerParameters(
            command=PYTHON_COMMAND,
            args=[MCP_SERVER_PATH],
            env=os.environ.copy(),
        )

        self._session: ClientSession | None = None

    @property
    def connected(self) -> bool:
        """
        현재 활성 MCP 세션이 존재하는지 반환한다.
        """
        return self._session is not None

    def _require_session(self) -> ClientSession:
        """
        활성 세션을 반환한다.

        연결되지 않은 상태에서 도구를 조회하거나 호출하면
        명확한 RuntimeError를 발생시킨다.
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
        MCP 서버를 실행하고 초기화된 세션을 제공한다.

        사용 예시:

            async with client.session():
                tools = await client.list_tools()
        """
        if self.connected:
            raise RuntimeError("MCP Client already has an active session.")

        async with stdio_client(self._server_parameters) as (
            read_stream,
            write_stream,
        ):
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
        MCP 서버가 제공하는 모든 도구의 목록을 요청한다.
        """
        session = self._require_session()
        return await session.list_tools()

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> CallToolResult:
        """
        MCP 서버의 도구 하나를 호출한다.

        Args:
            tool_name:
                호출할 MCP 도구 이름.

            arguments:
                도구에 전달할 입력값.
                입력이 없으면 빈 딕셔너리를 사용한다.

        Returns:
            MCP 서버가 반환한 CallToolResult.
        """
        if not tool_name.strip():
            raise ValueError("tool_name cannot be empty.")

        session = self._require_session()

        return await session.call_tool(
            tool_name,
            arguments=arguments or {},
        )