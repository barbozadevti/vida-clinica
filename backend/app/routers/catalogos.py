from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Agendamento,
    Atendimento,
    CatalogoCID,
    CatalogoCIAP,
    CatalogoExame,
    CatalogoMedicamento,
    Cidadao,
    Cobranca,
    ItemEstoque,
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
    ini = datetime.combine(datetime.now(timezone.utc).date(), time.min)
    hoje = date.today()
    cnt = lambda *w: db.scalar(select(func.count(Atendimento.id)).where(*w)) or 0

    prod = db.execute(
        select(Atendimento.profissional_id, func.count().label("n"))
        .where(Atendimento.status == "FINALIZADO", Atendimento.fim_atendimento >= ini)
        .group_by(Atendimento.profissional_id)
    ).all()
    nomes = {u.id: u.nome for u in db.scalars(select(Usuario))}

    agendamentos_hoje = db.scalar(
        select(func.count(Agendamento.id)).where(
            Agendamento.data == hoje, Agendamento.status.notin_(["CANCELADO"])
        )
    ) or 0
    estoque_baixo = db.scalar(
        select(func.count(ItemEstoque.id)).where(
            ItemEstoque.ativo == True, ItemEstoque.quantidade <= ItemEstoque.quantidade_minima  # noqa: E712
        )
    ) or 0
    faturamento_hoje = db.scalar(
        select(func.coalesce(func.sum(Cobranca.valor), 0)).where(
            Cobranca.status != "CANCELADO", func.date(Cobranca.criado_em) == hoje
        )
    ) or 0

    return PainelOut(
        aguardando=cnt(Atendimento.status == "AGUARDANDO"),
        sem_classificacao=cnt(Atendimento.status == "AGUARDANDO",
                              Atendimento.classificacao_risco.is_(None)),
        em_acolhimento_pendente=cnt(Atendimento.status == "AGUARDANDO",
                                    Atendimento.acolhido_em.is_(None)),
        em_atendimento=cnt(Atendimento.status == "EM_ATENDIMENTO"),
        finalizados_hoje=cnt(Atendimento.status == "FINALIZADO",
                             Atendimento.fim_atendimento >= ini),
        cidadaos=db.scalar(select(func.count(Cidadao.id))) or 0,
        retornos_7dias=cnt(Atendimento.desfecho == "RETORNO_AGENDADO",
                           Atendimento.retorno_data >= hoje,
                           Atendimento.retorno_data <= hoje + timedelta(days=7)),
        agendamentos_hoje=agendamentos_hoje,
        estoque_baixo=estoque_baixo,
        faturamento_hoje=float(faturamento_hoje),
        producao_hoje=[{"profissional": nomes.get(pid, "—"), "total": n}
                       for pid, n in prod],
    )
