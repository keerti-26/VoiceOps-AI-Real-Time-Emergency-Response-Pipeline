FROM python:3.11-bullseye

# Azure Speech SDK requires libssl1.1 and libasound2 (available on Debian Bullseye)
RUN apt-get update && apt-get install -y \
    libssl1.1 \
    libasound2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
