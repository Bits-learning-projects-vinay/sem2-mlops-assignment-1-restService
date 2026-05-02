# Use a slim Python image to keep the size down
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed for some ML libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
# This includes your model_service.py and any other scripts
COPY . .

# Expose the port your Flask app runs on
EXPOSE 8000

# Set environment variables (Defaults - can be overridden at runtime)
ENV PORT=8000
ENV MODEL_S3_REGION=ap-south-1

# Command to run the application using Gunicorn (recommended for production)
# If you haven't added gunicorn to requirements.txt, you can use:
# CMD ["python", "model_service.py"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "model_service:app"]