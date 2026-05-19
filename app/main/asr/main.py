import logging

from fastapi import FastAPI, HTTPException, Request

from service import transcribe_wav

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ASR Service (T-one)")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(request: Request) -> dict:
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty body")
    try:
        text = transcribe_wav(body)
    except Exception as exc:
        logger.exception("transcription failed")
        raise HTTPException(status_code=500, detail=f"asr error: {exc}") from exc
    return {"text": text}
