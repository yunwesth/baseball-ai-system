import os
import httpx

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Baseball Analytics MCP Server")

BASEBALL_API_URL = os.getenv(
    "BASEBALL_API_URL",
    "http://baseball-api:8000",
)


@mcp.tool()
async def analyze_player(
    name: str,
    avg: float,
    obp: float,
    slg: float,
) -> dict:

    payload = {
        "name": name,
        "avg": avg,
        "obp": obp,
        "slg": slg,
    }

    url = f"{BASEBALL_API_URL}/analyze-player"

    print("=" * 60)
    print("MCP Server Debug")
    print(f"BASEBALL_API_URL : {BASEBALL_API_URL}")
    print(f"Request URL      : {url}")
    print(f"Payload          : {payload}")
    print("=" * 60)

    try:

        async with httpx.AsyncClient(
            timeout=10,
            trust_env=False,
        ) as client:

            response = await client.post(
                url,
                json=payload,
            )

            print(f"HTTP Status : {response.status_code}")

            response.raise_for_status()

            result = response.json()

            print("Response JSON :", result)

            return result

    except Exception as e:

        print("Exception Type :", type(e).__name__)
        print("Exception      :", repr(e))

        raise


if __name__ == "__main__":
    mcp.run()