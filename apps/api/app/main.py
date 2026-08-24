from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data import DOCUMENTS, SUPPLIERS
from .models import AskRequest, AskResponse
from .service import recommend

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="Evidence Supply Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "deterministic-demo"}


@app.get("/api/suppliers")
def suppliers():
    return SUPPLIERS


@app.get("/api/documents")
def documents():
    return DOCUMENTS


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    return recommend(request)
