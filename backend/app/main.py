from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .bootstrap import inicializar
from .database import engine
from .routers import (
    atendimentos,
    auth,
    catalogos,
    cidadaos,
    documentos,
    fila,
    relatorios,
    usuarios,
)

app = FastAPI(
    title="e-SUS UBS — Prontuário / Atendimento",
    description="Fluxo padrão do atendimento na APS: fila, folha de rosto, "
    "registro SOAP, prescrição/atestado/exames e finalização com assinatura.",
    version="1.0.0",
)


@app.on_event("startup")
def _startup() -> None:
    try:
        inicializar()
    except Exception as exc:
        print(f"[startup] inicialização falhou: {exc}")


app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.middleware("http")
async def _sem_cache(request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith(("/api/", "/assets/")):
        resp.headers["Cache-Control"] = "no-store"
    return resp


for r in (auth, usuarios, cidadaos, fila, atendimentos, documentos, relatorios, catalogos):
    app.include_router(r.router)


@app.get("/api/health", tags=["health"])
def health():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as exc:
        return {"status": "degraded", "db": str(exc)}


FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND / "index.html")
