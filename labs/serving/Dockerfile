# Serve the exported model. Build after `python -m serve_lab export`:
#   docker build -t survey-topics:1 .
#   docker run --rm -p 8000:8000 survey-topics:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DIR=/app/model

WORKDIR /app

# Dependencies first: this layer is reused until the requirements change.
COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt

COPY src/ src/
COPY model/ model/
ENV PYTHONPATH=/app/src

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "serve_lab.app:build", "--factory", "--host", "0.0.0.0", "--port", "8000"]
