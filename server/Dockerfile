FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir tenseal boto3 numpy

COPY server.py .

RUN mkdir -p /app/data

CMD ["python", "server.py"]
