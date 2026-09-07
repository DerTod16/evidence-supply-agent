"""FastAPI 入口：静态页托管 + 查询 API + 真实资料导入 API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .data_loader import load_dataset_payload
from .models import AskRequest, AskResponse, EvidenceDocument, SourceProduct
from .service import recommend
from .store import store

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="Evidence Sourcing Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class ImportResponse(BaseModel):
    imported_products: int
    imported_documents: int
    is_demo: bool


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "deterministic-demo" if store.is_demo else "imported-dataset"}


@app.get("/api/products")
def products() -> list[SourceProduct]:
    return store.products


@app.get("/api/documents")
def documents() -> list[EvidenceDocument]:
    return store.documents


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    return recommend(request)


@app.post("/api/dataset/import", response_model=ImportResponse)
def import_dataset(payload: dict) -> ImportResponse:
    """以 examples/dataset.example.json 的结构上传自有货源资料，整体替换演示数据。"""
    try:
        products, docs = load_dataset_payload(payload)
        store.replace(products, docs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ImportResponse(
        imported_products=len(products),
        imported_documents=len(docs),
        is_demo=store.is_demo,
    )


@app.post("/api/dataset/reset")
def reset_dataset() -> ImportResponse:
    store.reset_demo()
    return ImportResponse(imported_products=len(store.products), imported_documents=len(store.documents), is_demo=True)
