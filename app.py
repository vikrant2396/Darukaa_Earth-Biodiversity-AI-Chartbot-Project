"""
FastAPI web layer for the Darukaa.Earth Biodiversity Intelligence system.

Run locally:
    uvicorn app:app --reload --port 8000
Then open http://localhost:8000

Deploy (for the "Live demo URL" submission requirement): this app has no external
dependencies beyond requirements.txt, so it deploys as-is to Render, Railway, Fly.io
or a Hugging Face Space (Docker SDK) with the start command:
    uvicorn app:app --host 0.0.0.0 --port $PORT
"""
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.conversation_manager import ConversationManager

app = FastAPI(
    title="Darukaa.Earth Biodiversity Intelligence API",
    description="Knowledge-grounded, multi-metric biodiversity reasoning system.",
    version="1.0.0",
)

manager = ConversationManager()

STATIC_DIR = Path(__file__).resolve().parent / "templates"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    text: Optional[str] = None
    structured: Optional[Dict[str, Any]] = None
    # Bonus: geo-coordinates / spatial context
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ChatResponse(BaseModel):
    session_id: str
    type: str
    message: str
    known_context: Dict[str, Any]
    recommendations: Optional[list] = None
    turn: int


@app.get("/")
def serve_ui():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    structured = dict(req.structured) if req.structured else {}
    if req.latitude is not None:
        structured["latitude"] = req.latitude
    if req.longitude is not None:
        structured["longitude"] = req.longitude

    result = manager.handle_message(session_id, text=req.text, structured=structured or None)
    return ChatResponse(session_id=session_id, **result)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
