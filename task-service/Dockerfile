FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home appuser

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

USER appuser

EXPOSE 5002

CMD ["sh", "-c", "python -c 'from app import init_db; init_db()' && gunicorn --bind 0.0.0.0:5002 --workers 2 --threads 2 --access-logfile - app:app"]
