"""
Command-line entry point for the Baseball AI Orchestrator.
"""

import argparse
import asyncio
import json
import sys
from typing import Sequence

from orchestrator import BaseballOrchestrator, OrchestratorError


def build_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line parser.
    """
    parser = argparse.ArgumentParser(
        description="Run Baseball AI orchestrator commands."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    analyze_parser = subparsers.add_parser(
        "analyze-player",
        help="Analyze one player's offensive statistics.",
    )

    analyze_parser.add_argument(
        "--name",
        required=True,
        help='Player name, for example "Aaron Judge".',
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

    return parser


async def run_command(args: argparse.Namespace) -> dict:
    """
    Run the selected command through the orchestrator.
    """
    orchestrator = BaseballOrchestrator()

    async with orchestrator.session():
        if args.command == "analyze-player":
            return await orchestrator.execute(
                action="analyze_player",
                arguments={
                    "name": args.name,
                    "avg": args.avg,
                    "obp": args.obp,
                    "slg": args.slg,
                },
            )

    raise ValueError(
        f"Unsupported command: {args.command}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """
    Parse CLI arguments, run the orchestrator, and print JSON output.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = asyncio.run(
            run_command(args)
        )
    except (
        ValueError,
        OrchestratorError,
        RuntimeError,
    ) as error:
        print(
            json.dumps(
                {
                    "error": str(error),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print(
            json.dumps(
                {
                    "error": "Operation cancelled by user.",
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 130

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
