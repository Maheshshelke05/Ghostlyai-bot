FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && mkdir -p /data/resumes && chown -R appuser /data /app
USER appuser

# Shell form so ${PORT} expands: Render (and similar PaaS hosts) inject PORT at runtime;
# falls back to 8000 for docker-compose / local use where PORT isn't set.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers
