FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p audio text cache

EXPOSE 8501

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
