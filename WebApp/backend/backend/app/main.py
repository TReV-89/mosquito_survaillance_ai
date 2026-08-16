import json
import os
import shutil
import uuid
from pydantic import BaseModel


from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.ml_engine import predict_mosquito_species
from app.utils import convert_to_mono_wav
from app.llm_engine import generate_insight


class InsightRequest(BaseModel):
    predictions: dict
    environment: str = "unknown"

app = FastAPI(title="VectorGuard AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".m4a", ".webm", ".flac", ".aac"}


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}


def validate_metadata(metadata: dict) -> dict:
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="Metadata must be a JSON object.")

    allowed_environment = {"indoor", "outdoor"}
    environment = metadata.get("environment")
    if environment is not None and environment not in allowed_environment:
        raise HTTPException(status_code=400, detail="Environment must be either 'indoor' or 'outdoor'.")

    location = metadata.get("location")
    if location is not None:
        if not isinstance(location, dict):
            raise HTTPException(status_code=400, detail="Location must be an object when provided.")
        if "lat" not in location or "lng" not in location:
            raise HTTPException(status_code=400, detail="Location must include 'lat' and 'lng'.")
        if not isinstance(location["lat"], (int, float)) or not isinstance(location["lng"], (int, float)):
            raise HTTPException(status_code=400, detail="Location coordinates must be numeric.")

    return metadata


@app.post("/api/v1/detect")
async def detect_mosquito(
    audio: UploadFile = File(...),
    metadata: str = Form(...)
):
    if not audio or not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    file_extension = Path(audio.filename).suffix.lower()
    if file_extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a common audio format such as wav, mp3, webm, or m4a.",
        )

    try:
        content = await audio.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read uploaded audio file.") from exc

    if not content or len(content) == 0:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    if len(content) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Audio file is too large. Maximum allowed size is 25MB.")

    if audio.content_type and not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not recognized as audio.")

    try:
        parsed_metadata = json.loads(metadata)
    except (TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Metadata must be valid JSON.")

    parsed_metadata = validate_metadata(parsed_metadata)

    try:
        session_id = str(uuid.uuid4())
        raw_path = UPLOAD_DIR / f"{session_id}{file_extension}"
        converted_wav_path = UPLOAD_DIR / f"{session_id}_clean.wav"

        with open(raw_path, "wb") as buffer:
            buffer.write(content)

        try:
            convert_to_mono_wav(str(raw_path), str(converted_wav_path), target_sample_rate=8000)
            predictions = predict_mosquito_species(str(converted_wav_path), parsed_metadata)
        finally:
            if raw_path.exists():
                raw_path.unlink()
            if converted_wav_path.exists():
                converted_wav_path.unlink()

        return {
            "status": "success",
            "session_id": session_id,
            "metadata_received": parsed_metadata,
            "predictions": predictions,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/api/v1/llm-insight")
async def llm_insight(payload: InsightRequest):
    try:
        insight = generate_insight(payload.predictions, payload.environment)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "success", "insight": insight}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
