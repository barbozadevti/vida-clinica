from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Agendamento, Atendimento, Cidadao, Usuario
from ...schemas import AgendamentoIn, AgendamentoOut, AtendimentoResumo
from ...security import exigir_perfis, usuario_atual
from ...util import com_vitais

router = APIRouter(prefix="/api/agenda", tags=["agenda"])
_RECEP = exigir_perfis("RECEPCAO", "ADMIN")

_STATUS = {"AGENDADO", "CONFIRMADO", "ATENDIDO", "FALTOU", "CANCELADO"}


@router.get("", response_model=list[AgendamentoOut])
def listar(data: date_cls | None = None, profissional_id: str | None = None,
           _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    stmt = select(Agendamento).order_by(Agendamento.data, Agendamento.hora)
    if data:
        stmt = stmt.where(Agendamento.data == data)
    if profissional_id:
        stmt = stmt.where(Agendamento.profissional_id == profissional_id)
    return db.scalars(stmt).all()


@router.post("", response_model=AgendamentoOut, status_code=201)
def criar(dados: AgendamentoIn, usuario: Usuario = Depends(_RECEP), db: Session = Depends(get_db)):
    if not db.get(Cidadao, dados.cidadao_id):
        raise HTTPException(400, "Cidadão inexistente")
    if not db.get(Usuario, dados.profissional_id):
        raise HTTPException(400, "Profissional inexistente")
    conflito = db.scalar(select(Agendamento).where(
        Agendamento.profissional_id == dados.profissional_id,
        Agendamento.data == dados.data, Agendamento.hora == dados.hora,
        Agendamento.status.notin_(["CANCELADO", "FALTOU"]),
    ))
    if conflito:
        raise HTTPException(409, "Já existe agendamento para este profissional neste horário")
    ag = Agendamento(**dados.model_dump(), criado_por_id=usuario.id)
    db.add(ag)
    db.commit()
    db.refresh(ag)
    return ag


@router.put("/{aid}", response_model=AgendamentoOut)
def atualizar(aid: str, dados: AgendamentoIn, _: Usuario = Depends(_RECEP), db: Session = Depends(get_db)):
    ag = db.get(Agendamento, aid)
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")
    if ag.status in ("ATENDIDO", "CANCELADO"):
        raise HTTPException(409, "Agendamento já encerrado não pode ser alterado")
    for k, v in dados.model_dump().items():
        setattr(ag, k, v)
    db.commit()
    db.refresh(ag)
    return ag


@router.post("/{aid}/status", response_model=AgendamentoOut)
def mudar_status(aid: str, status: str = Query(...),
                  _: Usuario = Depends(exigir_perfis("RECEPCAO", "ENFERMEIRO", "MEDICO")),
                  db: Session = Depends(get_db)):
    ag = db.get(Agendamento, aid)
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")
    status = status.upper()
    if status not in _STATUS:
        raise HTTPException(400, f"Status inválido: {sorted(_STATUS)}")
    ag.status = status
    db.commit()
    db.refresh(ag)
    return ag


@router.post("/{aid}/enviar-fila", response_model=AtendimentoResumo)
def enviar_para_fila(aid: str, usuario: Usuario = Depends(exigir_perfis("RECEPCAO", "ENFERMEIRO")),
                      db: Session = Depends(get_db)):
    """Chegada do paciente agendado: cria/abre o atendimento do dia (Passo 1)."""
    ag = db.get(Agendamento, aid)
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")
    if ag.status in ("CANCELADO", "ATENDIDO", "FALTOU"):
        raise HTTPException(409, "Agendamento não pode ser enviado à fila")
    ja = db.scalar(select(Atendimento).where(
        Atendimento.cidadao_id == ag.cidadao_id,
        Atendimento.status.in_(["AGUARDANDO", "EM_ATENDIMENTO"]),
    ))
    if ja:
        raise HTTPException(409, "Cidadão já está na fila de atendimento")
    at = Atendimento(cidadao_id=ag.cidadao_id, criado_por_id=usuario.id, status="AGUARDANDO",
                      tipo=ag.tipo, motivo=ag.observacao or "Consulta agendada")
    db.add(at)
    db.flush()
    ag.atendimento_id = at.id
    ag.status = "ATENDIDO"
    db.commit()
    db.refresh(at)
    return com_vitais(db, at)


@router.delete("/{aid}", status_code=204)
def cancelar(aid: str, _: Usuario = Depends(_RECEP), db: Session = Depends(get_db)):
    ag = db.get(Agendamento, aid)
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")
    ag.status = "CANCELADO"
    db.commit()
