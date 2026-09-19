from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import LogAcesso
from ...schemas import LogAcessoOut
from ...security import exigir_perfis

router = APIRouter(prefix="/api/auditoria", tags=["auditoria (LGPD)"])
_ADMIN = exigir_perfis("ADMIN")


@router.get("", response_model=list[LogAcessoOut])
def listar(
    de: date | None = None,
    ate: date | None = None,
    usuario_id: str | None = None,
    cidadao_id: str | None = None,
    atendimento_id: str | None = None,
    acao: str | None = None,
    _: str = Depends(_ADMIN),
    db: Session = Depends(get_db),
):
    """Consulta de auditoria — quem acessou/alterou o quê no prontuário e no
    financeiro. Restrito ao ADMIN: é o próprio registro de acesso, então não
    faz sentido cada perfil ver o log de todo mundo."""
    stmt = select(LogAcesso).order_by(LogAcesso.criado_em.desc()).limit(500)
    if de:
        stmt = stmt.where(LogAcesso.criado_em >= datetime.combine(de, time.min))
    if ate:
        stmt = stmt.where(LogAcesso.criado_em < datetime.combine(ate + timedelta(days=1), time.min))
    if usuario_id:
        stmt = stmt.where(LogAcesso.usuario_id == usuario_id)
    if cidadao_id:
        stmt = stmt.where(LogAcesso.cidadao_id == cidadao_id)
    if atendimento_id:
        stmt = stmt.where(LogAcesso.atendimento_id == atendimento_id)
    if acao:
        stmt = stmt.where(LogAcesso.acao == acao.upper())
    return db.scalars(stmt).all()
