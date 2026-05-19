"""
AI Calls Auth Service — FastAPI behind Traefik ForwardAuth.

External base path: /main (set via root_path so OpenAPI matches frontend).
Routes registered at /api/auth/* internally → /main/api/auth/* externally.
"""
import logging

from fastapi import FastAPI

from router import router as auth_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Calls Auth Service", root_path="/main")

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


@app.get("/health")
def health():
    return {"status": "ok"}
