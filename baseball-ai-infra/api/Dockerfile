# Use an official Python image as the starting point
# slim means it is smaller and lighter than the full Python image
FROM python:3.12-slim

# Set the working folder inside the container
# All future commands will run inside /app
WORKDIR /app

# Copy the requirements file from your computer into the container
# This file contains the Python packages we need
COPY requirements.txt .

# Install the Python packages listed in requirements.txt
# --no-cache-dir keeps the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project files into the container
# This includes main.py
COPY . .

# Tell Docker that the app inside the container uses port 8000
# Important: this is the container port, not the outside host port
EXPOSE 8000

# Start the FastAPI app using uvicorn
# main means main.py
# app means the FastAPI object named app inside main.py
# 0.0.0.0 allows outside connections into the container
# 8000 is the port inside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
