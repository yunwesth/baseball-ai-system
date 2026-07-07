
# Import os so we can read environment variables from Docker Compose

import os

# Import httpx so this MCP server can make HTTP requests to our REST API

import httpx

# Import FastMCP from the MCP Python SDK

# FastMCP lets us create MCP tools using simple Python decorators

from mcp.server.fastmcp import FastMCP

# Create the MCP server object

# This is like creating the "tool box" that AI clients can connect to

mcp = FastMCP("Baseball Analytics MCP Server")

# Read the Baseball REST API URL from an environment variable

# If Docker does not provide it, use http://baseball-api:8000 as the default

BASEBALL_API_URL = os.getenv("BASEBALL_API_URL", "http://baseball-api:8000")

# Define an MCP tool named analyze_player

# AI clients will be able to call this tool

@mcp.tool()

async def analyze_player(name: str, avg: float, obp: float, slg: float) -> dict:

    # Create the JSON data that we will send to the REST API

    payload = {

        "name": name,  # Player name

        "avg": avg,    # Batting average

        "obp": obp,    # On-base percentage

        "slg": slg     # Slugging percentage

    }

    # Create an async HTTP client

    # timeout=10 means the request fails if the REST API does not respond in 10 seconds

    async with httpx.AsyncClient(timeout=10) as client:

        # Send a POST request to the Baseball REST API endpoint

        response = await client.post(

            f"{BASEBALL_API_URL}/analyze-player",  # REST API endpoint URL

            json=payload                           # Send player stats as JSON

        )

        # Raise an error if the REST API returns a bad status code

        response.raise_for_status()

        # Convert the REST API JSON response into a Python dictionary

        result = response.json()

    # Return the REST API result back to the MCP client

    return result

# Start the MCP server when this file is run directly

if __name__ == "__main__":

    # Run the MCP server using stdio transport

    # stdio means the MCP client talks to this server through standard input/output

    mcp.run()

