# StoreLab — one Cloud Run service: API + web app + simulator + CV pipeline.

# ---------------------------------------------------------------- frontend build
# Builds frontend/ (React + Vite + TypeScript + Three.js) to frontend/dist. The repo has no
# web/ directory any more — this image is the only place one exists, assembled below from
# this stage's output (base: '/static/' in vite.config.ts matches storelab/main.py's mount).
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
# --legacy-peer-deps: openapi-typescript@7 peers on typescript@^5.x; this project runs TS 6.
# A plain `npm ci` re-validates peers strictly from a clean install and fails on that conflict
# even though local `npm install --legacy-peer-deps` already resolved it in the lockfile.
RUN npm ci --legacy-peer-deps
COPY frontend ./
RUN npm run build

# ---------------------------------------------------------------- python runtime
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY storelab ./storelab
COPY --from=frontend-build /app/frontend/dist ./web

# Build the synthetic world, fit the twin and render the demo clip now, so cold starts only load a cache.
# (This also proves OpenCV, NumPy and SciPy work inside the image: the build fails loudly if not.)
RUN python -m storelab.bootstrap

RUN useradd --create-home --uid 10001 storelab && chown -R storelab /app
USER storelab

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn storelab.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 75"]
