# syntax=docker/dockerfile:1

FROM node:20-slim AS frontend-build
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build


FROM python:3.12-slim AS backend
WORKDIR /app

RUN pip install --no-cache-dir \
    flask \
    flask-sqlalchemy \
    flask-cors \
    pg8000 \
    cloud-sql-python-connector \
    google-auth \
    python-dotenv \
    gunicorn

# This app only needs its own two modules (models.py, app.py), not the rest
# of rtgs_lab_tools -- and importing it as rtgs_lab_tools.device_monitoring.web_app.app
# requires the ancestor packages to exist, but NOT the real rtgs_lab_tools/__init__.py,
# which eagerly imports pandas/geopandas/streamlit/etc. So fabricate empty
# stand-ins for the ancestor packages instead of pulling in the whole monorepo.
RUN mkdir -p /app/rtgs_lab_tools/device_monitoring/web_app \
    && touch /app/rtgs_lab_tools/__init__.py \
    && touch /app/rtgs_lab_tools/device_monitoring/__init__.py

COPY __init__.py models.py app.py /app/rtgs_lab_tools/device_monitoring/web_app/
COPY --from=frontend-build /build/dist /app/rtgs_lab_tools/device_monitoring/web_app/dist

ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 rtgs_lab_tools.device_monitoring.web_app.app:app
