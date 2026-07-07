# Use an official Python image as the starting point
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the Python dependencies
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Start the MCP server
CMD ["python", "mcp_server.py"]