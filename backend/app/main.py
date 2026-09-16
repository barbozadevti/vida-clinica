from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .bootstrap import inicializar
from .database import engine
# Routers agrupados pelas ondas do MVP (ver "Lean Inception — Vida+ Clínica"):
# core        -> autenticação e administração, transversal aos dois MVPs
# prontuario  -> MVP 1, prontuário digital do atendimento
# gestao      -> MVP 2, fechamento financeiro do dia (agenda/convênios/financeiro/estoque)
# expansao    -> ondas 4/5, próximos MVPs (multiclínica, portal do paciente)
from .routers.core import auth, catalogos, relatorios, usuarios
from .routers.prontuario import atendimentos, cidadaos, documentos, fila
from .routers.gestao import agenda, convenios, estoque, financeiro
from .routers.expansao import portal, unidades

app = FastAPI(
    title="Vida+ Clínica — Sistema de Gestão Clínica",
    description="Sistema completo de gestão para clínicas e consultórios: agenda, "
    "recepção/fila, prontuário eletrônico com fluxo SOAP, prescrição/atestado/exames, "
    "financeiro (convênios e pagamentos), estoque e relatórios.",
    version="2.0.0",
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


for r in (auth, usuarios, cidadaos, fila, atendimentos, documentos, relatorios,
          catalogos, agenda, convenios, financeiro, estoque, unidades, portal):
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

    @app.get("/portal", include_in_schema=False)
    def portal_index():
        return FileResponse(FRONTEND / "portal.html")
