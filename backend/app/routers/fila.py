from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Atendimento, Cidadao, Usuario
from ..schemas import AtendimentoOut, AtendimentoResumo, FilaIn
from ..security import exigir_perfis, usuario_atual

router = APIRouter(prefix="/api/fila", tags=["fila (Passo 1)"])

_RISCO_ORDEM = {"VERMELHO": 0, "LARANJA": 1, "AMARELO": 2, "VERDE": 3, "AZUL": 4, None: 5}


@router.get("", response_model=list[AtendimentoResumo])
def listar_fila(_: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    """Lista de atendimento do dia: quem está AGUARDANDO ou EM_ATENDIMENTO."""
    inicio_dia = datetime.combine(datetime.now(timezone.utc).date(), time.min)
    itens = db.scalars(
        select(Atendimento)
        .where(
            Atendimento.status.in_(["AGUARDANDO", "EM_ATENDIMENTO"]),
            Atendimento.criado_em >= inicio_dia,
        )
    ).all()
    itens.sort(
        key=lambda a: (
            0 if a.status == "EM_ATENDIMENTO" else 1,
            _RISCO_ORDEM.get(a.classificacao_risco, 5),
            a.criado_em,
        )
    )
    return itens


@router.post("", response_model=AtendimentoResumo, status_code=201)
def adicionar(
    dados: FilaIn,
    usuario: Usuario = Depends(exigir_perfis("RECEPCAO", "ENFERMEIRO")),
    db: Session = Depends(get_db),
):
    if not db.get(Cidadao, dados.cidadao_id):
        raise HTTPException(400, "Cidadão inexistente")
    ja = db.scalar(
        select(Atendimento).where(
            Atendimento.cidadao_id == dados.cidadao_id,
            Atendimento.status.in_(["AGUARDANDO", "EM_ATENDIMENTO"]),
        )
    )
    if ja:
        raise HTTPException(409, "Cidadão já está na fila de atendimento")
    at = Atendimento(
        cidadao_id=dados.cidadao_id,
        criado_por_id=usuario.id,
        status="AGUARDANDO",
        tipo=dados.tipo,
        motivo=dados.motivo,
        classificacao_risco=dados.classificacao_risco,
    )
    db.add(at)
    db.commit()
    db.refresh(at)
    return at


@router.post("/{atendimento_id}/atender", response_model=AtendimentoOut)
def atender(
    atendimento_id: str,
    usuario: Usuario = Depends(exigir_perfis("MEDICO", "ENFERMEIRO")),
    db: Session = Depends(get_db),
):
    """Passo 1 — o profissional clica em 'Atender': abre o prontuário."""
    at = db.get(Atendimento, atendimento_id)
    if not at:
        raise HTTPException(404, "Atendimento não encontrado")
    if at.status == "FINALIZADO":
        raise HTTPException(409, "Atendimento já finalizado")
    if at.status == "EM_ATENDIMENTO" and at.profissional_id and str(at.profissional_id) != str(usuario.id):
        raise HTTPException(409, "Atendimento já está aberto por outro profissional")
    if at.status == "AGUARDANDO":
        at.status = "EM_ATENDIMENTO"
        at.profissional_id = usuario.id
        at.inicio_atendimento = datetime.now(timezone.utc)
        db.commit()
        db.refresh(at)
    return at


@router.post("/{atendimento_id}/cancelar", response_model=AtendimentoResumo)
def cancelar(
    atendimento_id: str,
    _: Usuario = Depends(exigir_perfis("RECEPCAO", "ENFERMEIRO", "MEDICO")),
    db: Session = Depends(get_db),
):
    at = db.get(Atendimento, atendimento_id)
    if not at:
        raise HTTPException(404, "Atendimento não encontrado")
    if at.status == "FINALIZADO":
        raise HTTPException(409, "Não é possível cancelar um atendimento finalizado")
    at.status = "CANCELADO"
    db.commit()
    db.refresh(at)
    return at
