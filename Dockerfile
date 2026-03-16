FROM python:3.11-slim

# System dependencies required by PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    mupdf \
    mupdf-tools \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying app code (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py agent.py rag.py tools.py file_processor.py ./
COPY static/ static/
COPY templates/ templates/
COPY data/ data/

# NOTE: model.pkl must exist in the build context before running
# docker-compose up. Generate it locally first with: python train.py
COPY model.pkl .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
