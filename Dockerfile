# Use a slim Python image for a smaller footprint
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory to /app
WORKDIR /app

# Install system dependencies (needed for some pandas/excel engines)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into /app
COPY ./app /app

# Expose the port FastAPI will run on
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "fast_main:app", "--host", "0.0.0.0", "--port", "8000"]