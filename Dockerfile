FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    HOUSECALLPRO_PORT=8080

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os, socket; s = socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', int(os.environ.get('HOUSECALLPRO_PORT', '8080')))); s.close()" || exit 1

CMD ["python", "housecallpro_server.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8080"]
