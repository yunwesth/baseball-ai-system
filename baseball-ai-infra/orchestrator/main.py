"""
Command-line entry point for the Baseball AI system.

Supported commands:

1. analyze-player
   Directly provide structured player statistics.

2. ask
   Provide a natural-language request.
   The LLM converts it into a structured command,
   and the orchestrator executes the corresponding MCP tool.
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Sequence

from llm import BaseballLLM, LLMError
from orchestrator import BaseballOrchestrator, OrchestratorError


def build_parser() -> argparse.ArgumentParser:
    """
    Create the command-line parser.
    """
    parser = argparse.ArgumentParser(
        description="Run Baseball AI commands.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # Direct structured command.
    analyze_parser = subparsers.add_parser(
        "analyze-player",
        help="Analyze a player using manually supplied statistics.",
    )

    analyze_parser.add_argument(
        "--name",
        required=True,
        help='Player name, such as "Aaron Judge".',
    )

    analyze_parser.add_argument(
        "--avg",
        required=True,
        type=float,
        help="Batting average between 0 and 1.",
    )

    analyze_parser.add_argument(
        "--obp",
        required=True,
        type=float,
        help="On-base percentage between 0 and 1.",
    )

    analyze_parser.add_argument(
        "--slg",
        required=True,
        type=float,
        help="Slugging percentage between 0 and 1.",
    )

    # Natural-language command.
    ask_parser = subparsers.add_parser(
        "ask",
        help="Analyze a natural-language baseball request.",
    )

    ask_parser.add_argument(
        "request",
        help=(
            "Natural-language request, for example: "
            '"Analyze Aaron Judge with a .322 AVG, '
            '.458 OBP, and .701 SLG."'
        ),
    )

    return parser


async def run_direct_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    """
    Execute a manually structured analyze-player command.
    """
    orchestrator = BaseballOrchestrator()

    async with orchestrator.session():
        return await orchestrator.execute(
            action="analyze_player",
            arguments={
                "name": args.name,
                "avg": args.avg,
                "obp": args.obp,
                "slg": args.slg,
            },
        )


async def run_natural_language_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    """
    Convert natural language into a structured command,
    then execute it through the orchestrator.
    """
    llm = BaseballLLM()

    # Step 1: Send the user's natural-language request to vLLM.
    tool_request = await llm.parse_request(
        args.request,
    )

    # Step 2: Send the structured command to the orchestrator.
    orchestrator = BaseballOrchestrator()

    async with orchestrator.session():
        return await orchestrator.execute(
            action=tool_request.action,
            arguments=tool_request.arguments,
        )


async def run_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    """
    Route the selected CLI command.
    """
    if args.command == "analyze-player":
        return await run_direct_command(args)

    if args.command == "ask":
        return await run_natural_language_command(args)

    raise ValueError(
        f"Unsupported command: {args.command}"
    )


def print_json(
    value: dict[str, Any],
    *,
    output_stream: Any = sys.stdout,
) -> None:
    """
    Print a dictionary as formatted JSON.
    """
    print(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        ),
        file=output_stream,
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """
    Parse arguments, run the selected command,
    and print the result.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = asyncio.run(
            run_command(args)
        )

    except (
        LLMError,
        OrchestratorError,
        ValueError,
        RuntimeError,
    ) as error:
        print_json(
            {
                "error": str(error),
            },
            output_stream=sys.stderr,
        )

        return 1

    except KeyboardInterrupt:
        print_json(
            {
                "error": "Operation cancelled by user.",
            },
            output_stream=sys.stderr,
        )

        return 130

    print_json(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
