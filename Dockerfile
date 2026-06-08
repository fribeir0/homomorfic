FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir tenseal boto3

COPY client.py .

RUN mkdir -p /app/keys /app/data

CMD ["python", "client.py"]
