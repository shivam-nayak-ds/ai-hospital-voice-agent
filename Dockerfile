FROM python:3.10-slim

WORKDIR /app

# Audio processing ke liye system tools
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    python3-all-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
