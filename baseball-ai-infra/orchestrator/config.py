"""
Configuration values for the Baseball AI orchestrator.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


ORCHESTRATOR_DIRECTORY = Path(__file__).resolve().parent

load_dotenv(
    dotenv_path=ORCHESTRATOR_DIRECTORY / ".env"
)


def read_boolean_environment_variable(
    name: str,
    default: bool = False,
) -> bool:
    """
    Read a boolean environment variable.
    """
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()

    if normalized_value in {
        "true",
        "1",
        "yes",
        "on",
    }:
        return True

    if normalized_value in {
        "false",
        "0",
        "no",
        "off",
    }:
        return False

    raise ValueError(
        f"{name} must be true or false, "
        f"but received {raw_value!r}."
    )


MCP_SERVER_PATH = str(
    (
        ORCHESTRATOR_DIRECTORY
        / "../mcp-server/mcp_server.py"
    ).resolve()
)

TIMEOUT_SECONDS = float(
    os.getenv(
        "TIMEOUT_SECONDS",
        "180",
    )
)

LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "http://127.0.0.1:8000/v1",
).rstrip("/")

LLM_MODEL_NAME = os.getenv(
    "LLM_MODEL_NAME",
    "",
).strip()

LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    "not-required",
)

LLM_TEMPERATURE = float(
    os.getenv(
        "LLM_TEMPERATURE",
        "0",
    )
)

BASEBALL_API_URL = os.getenv(
    "BASEBALL_API_URL",
    "http://127.0.0.1:8010",
).rstrip("/")

DEBUG = read_boolean_environment_variable(
    "DEBUG",
    default=False,
)
