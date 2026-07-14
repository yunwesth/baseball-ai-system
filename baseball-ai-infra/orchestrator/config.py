"""
Configuration values for the Baseball AI orchestrator.
"""

import os
from pathlib import Path


ORCHESTRATOR_DIRECTORY = Path(__file__).resolve().parent

MCP_SERVER_PATH = str(
    (
        ORCHESTRATOR_DIRECTORY
        / "../mcp-server/mcp_server.py"
    ).resolve()
)

PYTHON_COMMAND = os.getenv(
    "PYTHON_COMMAND",
    "python",
)

TIMEOUT_SECONDS = float(
    os.getenv("TIMEOUT_SECONDS", "30")
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
    os.getenv("LLM_TEMPERATURE", "0")
)
