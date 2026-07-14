"""
Baseball AI Orchestrator.

사용자의 요청을 받아 적절한 MCP 도구를 선택하고 실행한다.

현재 지원하는 작업:
- analyze_player

현재는 LLM 없이 명시적인 action과 arguments를 사용한다.
나중에 LLM이 자연어를 action/arguments 형태로 변환하게 된다.
"""

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.types import CallToolResult

from mcp_client import MCPClient


class OrchestratorError(RuntimeError):
    """
    Orchestrator 실행 과정에서 발생하는 오류.
    """


class BaseballOrchestrator:
    """
    Baseball AI 시스템의 중앙 제어 계층.

    역할:
    1. MCP 서버와 연결한다.
    2. 요청을 검증한다.
    3. 적절한 MCP 도구를 선택한다.
    4. MCP 도구의 결과를 Python dictionary로 반환한다.
    """

    SUPPORTED_ACTIONS = {
        "analyze_player",
    }

    def __init__(self) -> None:
        """
        MCP Client를 생성한다.

        이 시점에는 아직 MCP 서버가 실행되지 않는다.
        """
        self._mcp_client = MCPClient()
        self._started = False

    @property
    def started(self) -> bool:
        """
        Orchestrator가 활성 MCP 세션을 가지고 있는지 반환한다.
        """
        return self._started

    @asynccontextmanager
    async def session(self) -> AsyncIterator["BaseballOrchestrator"]:
        """
        MCP 서버와 연결된 Orchestrator 세션을 연다.

        사용 예시:

            async with orchestrator.session():
                result = await orchestrator.analyze_player(...)
        """
        if self._started:
            raise OrchestratorError(
                "Orchestrator session is already active."
            )

        async with self._mcp_client.session():
            self._started = True

            try:
                await self._verify_required_tools()
                yield self
            finally:
                self._started = False

    def _require_started(self) -> None:
        """
        활성 세션 없이 작업이 실행되는 것을 방지한다.
        """
        if not self._started:
            raise OrchestratorError(
                "Orchestrator is not active. "
                "Use 'async with orchestrator.session():' first."
            )

    async def _verify_required_tools(self) -> None:
        """
        MCP 서버에 필요한 도구들이 등록되어 있는지 확인한다.
        """
        tools_result = await self._mcp_client.list_tools()

        available_tools = {
            tool.name
            for tool in tools_result.tools
        }

        missing_tools = (
            self.SUPPORTED_ACTIONS - available_tools
        )

        if missing_tools:
            missing_text = ", ".join(sorted(missing_tools))

            raise OrchestratorError(
                f"Required MCP tools are missing: {missing_text}"
            )

    @staticmethod
    def _validate_player_name(name: str) -> str:
        """
        선수 이름을 검증하고 정리한다.
        """
        if not isinstance(name, str):
            raise ValueError("Player name must be a string.")

        cleaned_name = name.strip()

        if not cleaned_name:
            raise ValueError("Player name cannot be empty.")

        return cleaned_name

    @staticmethod
    def _validate_rate(
        field_name: str,
        value: float,
    ) -> float:
        """
        AVG, OBP, SLG 등의 비율 통계를 검증한다.

        현재 API에서는 0부터 1 사이의 값을 사용한다.
        """
        if isinstance(value, bool):
            raise ValueError(
                f"{field_name} must be a number."
            )

        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{field_name} must be a number."
            ) from error

        if not 0 <= numeric_value <= 1:
            raise ValueError(
                f"{field_name} must be between 0 and 1."
            )

        return numeric_value

    @staticmethod
    def _extract_tool_result(
        result: CallToolResult,
    ) -> dict[str, Any]:
        """
        MCP CallToolResult를 일반 Python dictionary로 변환한다.

        MCP 결과는 다음 두 방식 중 하나로 올 수 있다.

        1. structuredContent
        2. content 내부의 JSON 문자열
        """
        if result.isError:
            error_messages: list[str] = []

            for block in result.content:
                text = getattr(block, "text", None)

                if text:
                    error_messages.append(text)

            error_text = "\n".join(error_messages)

            if not error_text:
                error_text = "Unknown MCP tool error."

            raise OrchestratorError(error_text)

        structured_content = result.structuredContent

        if isinstance(structured_content, dict):
            return structured_content

        for block in result.content:
            text = getattr(block, "text", None)

            if not text:
                continue

            try:
                parsed_result = json.loads(text)
            except json.JSONDecodeError:
                continue

            if isinstance(parsed_result, dict):
                return parsed_result

        raise OrchestratorError(
            "The MCP tool returned no valid dictionary result."
        )

    async def execute(
        self,
        action: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        action 이름에 따라 적절한 Orchestrator 작업을 실행한다.

        나중에 LLM이 생성한 구조화된 명령도 이 메서드로 들어온다.

        예시:

            await orchestrator.execute(
                "analyze_player",
                {
                    "name": "Aaron Judge",
                    "avg": 0.322,
                    "obp": 0.458,
                    "slg": 0.701,
                },
            )
        """
        self._require_started()

        if not isinstance(action, str):
            raise ValueError("Action must be a string.")

        normalized_action = action.strip().lower()

        if normalized_action not in self.SUPPORTED_ACTIONS:
            supported = ", ".join(
                sorted(self.SUPPORTED_ACTIONS)
            )

            raise ValueError(
                f"Unsupported action: {action}. "
                f"Supported actions: {supported}"
            )

        if not isinstance(arguments, dict):
            raise ValueError(
                "Arguments must be a dictionary."
            )

        if normalized_action == "analyze_player":
            return await self.analyze_player(
                name=arguments.get("name"),
                avg=arguments.get("avg"),
                obp=arguments.get("obp"),
                slg=arguments.get("slg"),
            )

        raise OrchestratorError(
            f"No handler was implemented for: {normalized_action}"
        )

    async def analyze_player(
        self,
        name: str,
        avg: float,
        obp: float,
        slg: float,
    ) -> dict[str, Any]:
        """
        선수의 공격 통계를 Baseball API로 분석한다.
        """
        self._require_started()

        validated_name = self._validate_player_name(name)

        validated_avg = self._validate_rate(
            "avg",
            avg,
        )

        validated_obp = self._validate_rate(
            "obp",
            obp,
        )

        validated_slg = self._validate_rate(
            "slg",
            slg,
        )

        tool_result = await self._mcp_client.call_tool(
            "analyze_player",
            {
                "name": validated_name,
                "avg": validated_avg,
                "obp": validated_obp,
                "slg": validated_slg,
            },
        )

        return self._extract_tool_result(tool_result)