"""ASGI entry point: uvicorn storelab.main:app --port 8080."""

from .api.application import create_app

app = create_app()
