# Import FastAPI, the tool that lets us build a REST API
from fastapi import FastAPI

# Import BaseModel, which helps us define what data the API should receive
from pydantic import BaseModel

# Create the FastAPI app object
# This is the main API application
app = FastAPI(
    title="Baseball Analytics API",  # The name of our API
    description="A RESTful API for baseball player analysis.",  # Short explanation of the API
    version="0.1.0"  # Version number of our API
)

# Create a data model for player stats
# This tells the API what kind of JSON data we expect from the user
class PlayerStats(BaseModel):
    name: str  # Player name must be text
    avg: float  # Batting average must be a number
    obp: float  # On-base percentage must be a number
    slg: float  # Slugging percentage must be a number

# Create a GET endpoint for the home page
# When someone visits "/", this function runs
@app.get("/")
def home():
    # Return a JSON response
    return {
        "message": "Baseball Analytics API is running",  # Main response message
        "docs": "/docs"  # Tells user where the API documentation is
    }

# Create a GET endpoint to check if the API is alive
# This is useful for testing and monitoring
@app.get("/health")
def health():
    # Return a simple status response
    return {
        "status": "ok"  # Means the API server is working
    }

# Create a POST endpoint to analyze one baseball player
# POST means the user sends data to the API
@app.post("/analyze-player")
def analyze_player(player: PlayerStats):
    # Calculate OPS by adding OBP and SLG
    ops = player.obp + player.slg

    # Decide the player's offensive level based on OPS
    if ops >= 0.900:
        level = "excellent"  # OPS 0.900 or higher is excellent
    elif ops >= 0.800:
        level = "good"  # OPS 0.800 to 0.899 is good
    elif ops >= 0.700:
        level = "average"  # OPS 0.700 to 0.799 is average
    else:
        level = "needs improvement"  # OPS below 0.700 needs improvement

    # Return the analysis as JSON
    return {
        "player": player.name,  # Return the player's name
        "avg": player.avg,  # Return batting average
        "obp": player.obp,  # Return on-base percentage
        "slg": player.slg,  # Return slugging percentage
        "ops": round(ops, 3),  # Return OPS rounded to 3 decimals
        "analysis": f"{player.name} has a {level} offensive profile."  # Human-readable analysis
    }
