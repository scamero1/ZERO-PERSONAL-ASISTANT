FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential ffmpeg libsndfile1 \
 && pip install --no-cache-dir -r /app/requirements.txt \
 && apt-get remove -y build-essential \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8501

CMD ["streamlit", "run", "Zero.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
