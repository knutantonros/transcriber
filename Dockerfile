FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (ffmpeg)
COPY packages.txt .
RUN apt-get update && \
    xargs apt-get install -y < packages.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create directories for audio and text files
RUN mkdir -p audio text cache

# Set environment variables for Streamlit
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Expose the port Streamlit runs on
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
