FROM python:3.12-slim

# Ensures print()/logging output is flushed immediately, so `docker compose
# logs` shows log lines in real time instead of buffering them.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["python", "app.py"]
