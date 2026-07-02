FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi uvicorn

COPY config ./config
COPY paper_radar ./paper_radar

RUN mkdir -p data/logs notes/daily notes/papers

EXPOSE 8010

CMD ["uvicorn", "paper_radar.api:app", "--host", "0.0.0.0", "--port", "8010"]
