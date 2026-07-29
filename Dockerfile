# syntax=docker/dockerfile:1

FROM node:22.23.1-slim AS frontend

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim-bookworm AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --create-home app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app manage.py ./
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app --from=frontend /app/frontend/dist ./frontend/dist

RUN DJANGO_SECRET_KEY=collectstatic-only \
    python manage.py collectstatic --noinput

USER app

EXPOSE 8000

STOPSIGNAL SIGTERM

CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
