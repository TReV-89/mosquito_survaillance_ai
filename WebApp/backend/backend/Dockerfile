FROM python:3.10-slim

# Install system dependencies (ffmpeg for pydub audio conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install CPU-optimized PyTorch & dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.2.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy model weights and application source code
COPY model/ ./model/
COPY app/ ./app/

# Expose port (Render automatically sets PORT)
ENV PORT=8000
EXPOSE 8000

# Run FastAPI backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
