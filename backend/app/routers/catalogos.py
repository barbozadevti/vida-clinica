from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Atendimento,
    CatalogoCID,
    CatalogoCIAP,
    CatalogoExame,
    CatalogoMedicamento,
    Cidadao,
    Usuario,
)
from ..schemas import (
    CodigoOut,
    ExameCatalogoOut,
    MedicamentoCatalogoOut,
    PainelOut,
)
from ..security import usuario_atual

router = APIRouter(prefix="/api", tags=["catálogos"])


@router.get("/catalogo/medicamentos", response_model=list[MedicamentoCatalogoOut])
def medicamentos(q: str | None = Query(default=None), _: Usuario = Depends(usuario_atual),
                 db: Session = Depends(get_db)):
    stmt = select(CatalogoMedicamento).order_by(CatalogoMedicamento.nome).limit(50)
    if q:
        t = f"%{q}%"
        stmt = stmt.where(or_(CatalogoMedicamento.nome.ilike(t),
                              CatalogoMedicamento.principio_ativo.ilike(t)))
    return db.scalars(stmt).all()


@router.get("/catalogo/cid10", response_model=list[CodigoOut])
def cid10(q: str | None = Query(default=None), _: Usuario = Depends(usuario_atual),
          db: Session = Depends(get_db)):
    stmt = select(CatalogoCID).order_by(CatalogoCID.codigo).limit(50)
    if q:
        t = f"%{q}%"
        stmt = stmt.where(or_(CatalogoCID.codigo.ilike(t), CatalogoCID.descricao.ilike(t)))
    return db.scalars(stmt).all()


@router.get("/catalogo/ciap2", response_model=list[CodigoOut])
def ciap2(q: str | None = Query(default=None), _: Usuario = Depends(usuario_atual),
          db: Session = Depends(get_db)):
    stmt = select(CatalogoCIAP).order_by(CatalogoCIAP.codigo).limit(50)
    if q:
        t = f"%{q}%"
        stmt = stmt.where(or_(CatalogoCIAP.codigo.ilike(t), CatalogoCIAP.descricao.ilike(t)))
    return db.scalars(stmt).all()


@router.get("/catalogo/exames", response_model=list[ExameCatalogoOut])
def exames(q: str | None = Query(default=None), _: Usuario = Depends(usuario_atual),
           db: Session = Depends(get_db)):
    stmt = select(CatalogoExame).order_by(CatalogoExame.nome).limit(50)
    if q:
        t = f"%{q}%"
        stmt = stmt.where(or_(CatalogoExame.nome.ilike(t), CatalogoExame.sinonimia.ilike(t)))
    return db.scalars(stmt).all()


@router.get("/painel", response_model=PainelOut, tags=["painel"])
def painel(_: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    inicio_dia = datetime.combine(datetime.now(timezone.utc).date(), time.min)
    return PainelOut(
        aguardando=db.scalar(select(func.count(Atendimento.id)).where(
            Atendimento.status == "AGUARDANDO")) or 0,
        em_atendimento=db.scalar(select(func.count(Atendimento.id)).where(
            Atendimento.status == "EM_ATENDIMENTO")) or 0,
        finalizados_hoje=db.scalar(select(func.count(Atendimento.id)).where(
            Atendimento.status == "FINALIZADO",
            Atendimento.fim_atendimento >= inicio_dia)) or 0,
        cidadaos=db.scalar(select(func.count(Cidadao.id))) or 0,
    )
