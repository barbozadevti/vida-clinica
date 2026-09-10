import io
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Atendimento, ProblemaAtendimento, Usuario
from ..schemas import AtendimentoResumo, ProducaoOut
from ..security import exigir_perfis, usuario_atual

router = APIRouter(prefix="/api/relatorios", tags=["relatórios"])
_GESTAO = exigir_perfis("MEDICO", "ENFERMEIRO")


def _intervalo(de: str | None, ate: str | None):
    hoje = date.today()
    d0 = datetime.strptime(de, "%Y-%m-%d").date() if de else hoje.replace(day=1)
    d1 = datetime.strptime(ate, "%Y-%m-%d").date() if ate else hoje
    return d0, d1, datetime.combine(d0, time.min), datetime.combine(d1 + timedelta(days=1), time.min)


@router.get("/producao", response_model=ProducaoOut)
def producao(
    de: str | None = Query(default=None), ate: str | None = Query(default=None),
    profissional_id: str | None = None,
    _: Usuario = Depends(_GESTAO), db: Session = Depends(get_db),
):
    d0, d1, ini, fim = _intervalo(de, ate)
    base = select(Atendimento).where(
        Atendimento.status == "FINALIZADO",
        Atendimento.fim_atendimento >= ini, Atendimento.fim_atendimento < fim,
    )
    if profissional_id:
        base = base.where(Atendimento.profissional_id == profissional_id)
    ats = db.scalars(base).all()
    ids = [a.id for a in ats]

    por_prof: dict[str, int] = {}
    por_des: dict[str, int] = {}
    por_risco: dict[str, int] = {}
    for a in ats:
        nome = a.profissional.nome if a.profissional else "—"
        por_prof[nome] = por_prof.get(nome, 0) + 1
        por_des[a.desfecho or "—"] = por_des.get(a.desfecho or "—", 0) + 1
        por_risco[a.classificacao_risco or "—"] = por_risco.get(a.classificacao_risco or "—", 0) + 1

    por_cid: list[dict] = []
    if ids:
        rows = db.execute(
            select(ProblemaAtendimento.codigo, ProblemaAtendimento.descricao,
                   func.count().label("n"))
            .where(ProblemaAtendimento.atendimento_id.in_(ids))
            .group_by(ProblemaAtendimento.codigo, ProblemaAtendimento.descricao)
            .order_by(func.count().desc()).limit(15)
        ).all()
        por_cid = [{"codigo": r[0], "descricao": r[1], "total": r[2]} for r in rows]

    ordena = lambda d: [{"nome": k, "total": v} for k, v in sorted(d.items(), key=lambda x: -x[1])]
    return ProducaoOut(
        periodo_de=d0, periodo_ate=d1, total=len(ats),
        por_profissional=ordena(por_prof), por_desfecho=ordena(por_des),
        por_risco=ordena(por_risco), por_cid=por_cid,
    )


@router.get("/producao.csv")
def producao_csv(
    de: str | None = None, ate: str | None = None,
    _: Usuario = Depends(_GESTAO), db: Session = Depends(get_db),
):
    d0, d1, ini, fim = _intervalo(de, ate)
    ats = db.scalars(
        select(Atendimento).where(
            Atendimento.status == "FINALIZADO",
            Atendimento.fim_atendimento >= ini, Atendimento.fim_atendimento < fim,
        ).order_by(Atendimento.fim_atendimento)
    ).all()
    buf = io.StringIO()
    buf.write("data;cidadao;profissional;tipo;risco;desfecho;cids\n")
    for a in ats:
        cids = " | ".join(f"{p.codigo}" for p in a.problemas)
        buf.write(";".join([
            a.fim_atendimento.strftime("%d/%m/%Y %H:%M") if a.fim_atendimento else "",
            (a.cidadao.nome_completo if a.cidadao else "").replace(";", ","),
            (a.profissional.nome if a.profissional else "").replace(";", ","),
            a.tipo, a.classificacao_risco or "", a.desfecho or "", cids,
        ]) + "\n")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="producao_{d0}_{d1}.csv"'},
    )


@router.get("/retornos", response_model=list[AtendimentoResumo])
def retornos(
    dias: int = Query(default=14, ge=1, le=90),
    _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db),
):
    hoje = date.today()
    return db.scalars(
        select(Atendimento).where(
            Atendimento.desfecho == "RETORNO_AGENDADO",
            Atendimento.retorno_data >= hoje,
            Atendimento.retorno_data <= hoje + timedelta(days=dias),
        ).order_by(Atendimento.retorno_data)
    ).all()
