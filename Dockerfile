# StoreLab — one Cloud Run service: API + web app + simulator + CV pipeline.
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
COPY web ./web

# Build the synthetic world, fit the twin and render the demo clip now, so cold starts only load a cache.
# (This also proves OpenCV, NumPy and SciPy work inside the image: the build fails loudly if not.)
RUN python -m storelab.bootstrap

RUN useradd --create-home --uid 10001 storelab && chown -R storelab /app
USER storelab

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn storelab.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 75"]
