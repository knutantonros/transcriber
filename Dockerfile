FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Create directories needed by the app
RUN mkdir -p audio text cache

# Expose port for Streamlit
EXPOSE 8501

# Set up environment variables
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Command to run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
