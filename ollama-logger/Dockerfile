FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY logger.py .
COPY config.yaml .

EXPOSE 11435

CMD ["python", "logger.py"]
