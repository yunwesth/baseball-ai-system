"""
Baseball AI Orchestrator.

Receives user requests, selects the appropriate MCP tool, and executes it.

Currently supported actions:
- analyze_player

Currently uses explicit action and arguments without an LLM.
In the future, an LLM will convert natural language into action/arguments form.
"""

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.types import CallToolResult

from mcp_client import MCPClient


class OrchestratorError(RuntimeError):
    """
    Error raised during Orchestrator execution.
    """


class BaseballOrchestrator:
    """
    Central control layer of the Baseball AI system.

    Responsibilities:
    1. Connect to the MCP server.
    2. Validate requests.
    3. Select the appropriate MCP tool.
    4. Return MCP tool results as a Python dictionary.
    """

    SUPPORTED_ACTIONS = {
        "analyze_player",
    }

    def __init__(self) -> None:
        """
        Creates the MCP Client.

        The MCP server is not yet running at this point.
        """
        self._mcp_client = MCPClient()
        self._started = False

    @property
    def started(self) -> bool:
        """
        Returns whether the Orchestrator has an active MCP session.
        """
        return self._started

    @asynccontextmanager
    async def session(self) -> AsyncIterator["BaseballOrchestrator"]:
        """
        Opens an Orchestrator session connected to the MCP server.

        Usage:

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
        Prevents operations from running without an active session.
        """
        if not self._started:
            raise OrchestratorError(
                "Orchestrator is not active. "
                "Use 'async with orchestrator.session():' first."
            )

    async def _verify_required_tools(self) -> None:
        """
        Verifies that the required tools are registered on the MCP server.
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
        Validates and sanitizes a player name.
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
        Validates rate statistics such as AVG, OBP, and SLG.

        The current API expects values between 0 and 1.
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
        Converts an MCP CallToolResult into a plain Python dictionary.

        The MCP result can arrive in one of two forms:

        1. structuredContent
        2. A JSON string inside content
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
        Executes the appropriate Orchestrator operation based on the action name.

        Structured commands generated by an LLM will also enter through this method.

        Example:

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
        Analyzes a player's offensive statistics using the Baseball API.
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