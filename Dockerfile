# Multi-stage build: build the React frontend, then serve it from the FastAPI backend.
# Result: one container, one URL — the backend serves /api AND the built UI.

# ---- Stage 1: build the frontend ----
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # -> /app/frontend/dist

# ---- Stage 2: python runtime ----
FROM python:3.11-slim
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
# place the built UI where FastAPI serves it (backend/static)
COPY --from=frontend /app/frontend/dist ./static

EXPOSE 8000
# PORT is provided by the host (Render/Railway); default 8000 locally.
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
