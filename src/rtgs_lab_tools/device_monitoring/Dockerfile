# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project to maintain import structure
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PORT=8080

# Change to the device_monitoring directory
WORKDIR /app/src/rtgs_lab_tools/device_monitoring

# Run the Flask app
CMD ["python", "app.py"]