from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Atendimento, Cidadao, Medicao, Usuario
from ...schemas import AcolhimentoIn, AtendimentoOut, AtendimentoResumo, FilaIn
from ...security import exigir_perfis, usuario_atual
from ...util import com_vitais

router = APIRouter(prefix="/api/fila", tags=["fila (Passo 1)"])

_RISCO_ORDEM = {"VERMELHO": 0, "LARANJA": 1, "AMARELO": 2, "VERDE": 3, "AZUL": 4, None: 5}
_VITAIS = {
    "pa_sistolica": ("PA_SISTOLICA", "mmHg"), "pa_diastolica": ("PA_DIASTOLICA", "mmHg"),
    "peso": ("PESO", "kg"), "altura": ("ALTURA", "cm"), "temperatura": ("TEMPERATURA", "°C"),
    "freq_cardiaca": ("FC", "bpm"), "freq_respiratoria": ("FR", "irpm"),
    "saturacao": ("SATO2", "%"), "glicemia": ("GLICEMIA", "mg/dL"),
}


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


@router.post("/{atendimento_id}/acolhimento", response_model=AtendimentoResumo)
def acolhimento(
    atendimento_id: str,
    dados: AcolhimentoIn,
    usuario: Usuario = Depends(exigir_perfis("ENFERMEIRO")),
    db: Session = Depends(get_db),
):
    """Acolhimento / pré-consulta da enfermagem: sinais vitais + classificação de risco."""
    at = db.get(Atendimento, atendimento_id)
    if not at:
        raise HTTPException(404, "Atendimento não encontrado")
    if at.status not in ("AGUARDANDO", "EM_ATENDIMENTO"):
        raise HTTPException(409, "Atendimento não está na fila")

    if dados.classificacao_risco:
        at.classificacao_risco = dados.classificacao_risco
    if dados.motivo:
        at.motivo = dados.motivo
    at.acolhimento = dados.anotacao
    at.acolhido_por_id = usuario.id
    at.acolhido_em = datetime.now(timezone.utc)

    db.query(Medicao).filter(
        Medicao.atendimento_id == at.id, Medicao.tipo.in_([t for t, _ in _VITAIS.values()])
    ).delete(synchronize_session=False)
    agora = datetime.now(timezone.utc)
    v = dados.model_dump()
    for campo, (tipo, unidade) in _VITAIS.items():
        if v.get(campo) is not None:
            db.add(Medicao(cidadao_id=at.cidadao_id, atendimento_id=at.id,
                           tipo=tipo, valor=float(v[campo]), unidade=unidade, aferido_em=agora))
    if v.get("peso") and v.get("altura") and float(v["altura"]) > 0:
        imc = round(float(v["peso"]) / (float(v["altura"]) / 100) ** 2, 1)
        db.add(Medicao(cidadao_id=at.cidadao_id, atendimento_id=at.id,
                       tipo="IMC", valor=imc, unidade="kg/m²", aferido_em=agora))
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
    return com_vitais(db, at)


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
