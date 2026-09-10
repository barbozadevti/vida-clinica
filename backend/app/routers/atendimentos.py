from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Alergia,
    Atendimento,
    Encaminhamento,
    Medicao,
    MedicamentoEmUso,
    ProblemaAtendimento,
    Usuario,
)
from ..schemas import (
    AtendimentoOut,
    AtendimentoResumo,
    FinalizarIn,
    FolhaRostoOut,
    ProblemaIn,
    ProblemaOut,
    SerieEvolucao,
    SoapIn,
)
from ..security import exigir_perfis, usuario_atual
from ..util import cidadao_dict

router = APIRouter(prefix="/api/atendimentos", tags=["atendimento (Passos 2, 3, 5)"])
_CLINICO = exigir_perfis("MEDICO", "ENFERMEIRO")

DESFECHOS = {
    "ALTA", "RETORNO_AGENDADO", "ENCAMINHAMENTO", "OBSERVACAO",
    "ENCAMINHAMENTO_URGENCIA",
}

# mapeia campos estruturados do SOAP-O -> (tipo, unidade)
VITAIS = {
    "pa_sistolica": ("PA_SISTOLICA", "mmHg"),
    "pa_diastolica": ("PA_DIASTOLICA", "mmHg"),
    "peso": ("PESO", "kg"),
    "altura": ("ALTURA", "cm"),
    "temperatura": ("TEMPERATURA", "°C"),
    "freq_cardiaca": ("FC", "bpm"),
    "freq_respiratoria": ("FR", "irpm"),
    "saturacao": ("SATO2", "%"),
    "glicemia": ("GLICEMIA", "mg/dL"),
}


def _get(db: Session, aid: str) -> Atendimento:
    at = db.get(Atendimento, aid)
    if not at:
        raise HTTPException(404, "Atendimento não encontrado")
    return at


def _pode_editar(at: Atendimento, usuario: Usuario) -> None:
    if at.assinado or at.status == "FINALIZADO":
        raise HTTPException(409, "Atendimento finalizado/assinado — não pode ser alterado")
    if at.profissional_id and str(at.profissional_id) != str(usuario.id):
        raise HTTPException(403, "Este atendimento está sob responsabilidade de outro profissional")


@router.get("", response_model=list[AtendimentoResumo])
def listar(cidadao_id: str | None = None, _: Usuario = Depends(usuario_atual),
           db: Session = Depends(get_db)):
    stmt = select(Atendimento).order_by(Atendimento.criado_em.desc()).limit(200)
    if cidadao_id:
        stmt = stmt.where(Atendimento.cidadao_id == cidadao_id)
    return db.scalars(stmt).all()


@router.get("/{aid}", response_model=AtendimentoOut)
def obter(aid: str, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return _get(db, aid)


# ─────────── Passo 2 — Folha de Rosto ───────────
@router.get("/{aid}/folha-rosto", response_model=FolhaRostoOut)
def folha_rosto(aid: str, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    at = _get(db, aid)
    cid = at.cidadao_id

    _peso_grav = {"GRAVE": 0, "MODERADA": 1, "LEVE": 2}
    alergias = sorted(
        db.scalars(
            select(Alergia).where(
                Alergia.cidadao_id == cid, Alergia.ativo == True  # noqa: E712
            )
        ).all(),
        key=lambda a: (_peso_grav.get(a.gravidade, 3), a.substancia),
    )
    medicamentos = db.scalars(
        select(MedicamentoEmUso).where(
            MedicamentoEmUso.cidadao_id == cid, MedicamentoEmUso.ativo == True  # noqa: E712
        )
    ).all()
    anteriores = db.scalars(
        select(Atendimento).where(
            Atendimento.cidadao_id == cid,
            Atendimento.id != at.id,
            Atendimento.status == "FINALIZADO",
        ).order_by(Atendimento.criado_em.desc()).limit(20)
    ).all()

    medicoes = db.scalars(
        select(Medicao).where(Medicao.cidadao_id == cid).order_by(Medicao.aferido_em)
    ).all()
    series: dict[str, SerieEvolucao] = {}
    for m in medicoes:
        s = series.get(m.tipo)
        if not s:
            s = SerieEvolucao(tipo=m.tipo, unidade=m.unidade, pontos=[])
            series[m.tipo] = s
        s.pontos.append({"data": m.aferido_em.isoformat(), "valor": m.valor})

    return FolhaRostoOut(
        cidadao=cidadao_dict(at.cidadao),
        alergias=alergias,
        medicamentos_ativos=medicamentos,
        consultas_anteriores=anteriores,
        evolucao=[series[k] for k in ("PA_SISTOLICA", "PA_DIASTOLICA", "PESO", "IMC",
                                      "GLICEMIA", "TEMPERATURA") if k in series]
        + [v for k, v in series.items()
           if k not in ("PA_SISTOLICA", "PA_DIASTOLICA", "PESO", "IMC", "GLICEMIA", "TEMPERATURA")],
    )


# ─────────── Passo 3 — Registro SOAP ───────────
@router.put("/{aid}/soap", response_model=AtendimentoOut)
def salvar_soap(aid: str, dados: SoapIn, usuario: Usuario = Depends(_CLINICO),
                db: Session = Depends(get_db)):
    at = _get(db, aid)
    _pode_editar(at, usuario)
    if at.status == "AGUARDANDO":  # abre automaticamente ao começar a registrar
        at.status = "EM_ATENDIMENTO"
        at.profissional_id = usuario.id
        at.inicio_atendimento = datetime.now(timezone.utc)

    at.subjetivo = dados.subjetivo
    at.objetivo = dados.objetivo
    at.avaliacao = dados.avaliacao
    at.plano = dados.plano

    # regrava os sinais vitais estruturados deste atendimento
    db.execute(delete(Medicao).where(Medicao.atendimento_id == at.id))
    agora = datetime.now(timezone.utc)
    valores = dados.model_dump()
    for campo, (tipo, unidade) in VITAIS.items():
        v = valores.get(campo)
        if v is not None:
            db.add(Medicao(cidadao_id=at.cidadao_id, atendimento_id=at.id,
                           tipo=tipo, valor=float(v), unidade=unidade, aferido_em=agora))
    if valores.get("peso") and valores.get("altura"):
        altura_m = float(valores["altura"]) / 100
        if altura_m > 0:
            imc = round(float(valores["peso"]) / (altura_m ** 2), 1)
            db.add(Medicao(cidadao_id=at.cidadao_id, atendimento_id=at.id,
                           tipo="IMC", valor=imc, unidade="kg/m²", aferido_em=agora))
    db.commit()
    db.refresh(at)
    return at


@router.post("/{aid}/problemas", response_model=ProblemaOut, status_code=201)
def add_problema(aid: str, dados: ProblemaIn, usuario: Usuario = Depends(_CLINICO),
                 db: Session = Depends(get_db)):
    at = _get(db, aid)
    _pode_editar(at, usuario)
    p = ProblemaAtendimento(atendimento_id=at.id, **dados.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{aid}/problemas/{pid}", status_code=204)
def del_problema(aid: str, pid: str, usuario: Usuario = Depends(_CLINICO),
                 db: Session = Depends(get_db)):
    at = _get(db, aid)
    _pode_editar(at, usuario)
    p = db.get(ProblemaAtendimento, pid)
    if not p or str(p.atendimento_id) != aid:
        raise HTTPException(404, "Problema não encontrado")
    db.delete(p)
    db.commit()


# ─────────── Passo 5 — Finalização e assinatura ───────────
@router.post("/{aid}/finalizar", response_model=AtendimentoOut)
def finalizar(aid: str, dados: FinalizarIn, usuario: Usuario = Depends(_CLINICO),
              db: Session = Depends(get_db)):
    at = _get(db, aid)
    _pode_editar(at, usuario)
    desfecho = dados.desfecho.upper()
    if desfecho not in DESFECHOS:
        raise HTTPException(400, f"Desfecho inválido. Use um de: {sorted(DESFECHOS)}")
    if not (at.avaliacao or at.problemas):
        raise HTTPException(400, "Registre a Avaliação (A) antes de finalizar")
    if desfecho in ("ENCAMINHAMENTO", "ENCAMINHAMENTO_URGENCIA"):
        if not (dados.encaminhamento_especialidade and dados.encaminhamento_motivo):
            raise HTTPException(400, "Informe especialidade e motivo do encaminhamento")
        db.add(Encaminhamento(
            atendimento_id=at.id,
            especialidade=dados.encaminhamento_especialidade,
            motivo=dados.encaminhamento_motivo,
            prioridade=(dados.encaminhamento_prioridade or "ROTINA").upper(),
        ))
    if desfecho == "RETORNO_AGENDADO" and not dados.retorno_data:
        raise HTTPException(400, "Informe a data do retorno")

    at.desfecho = desfecho
    at.desfecho_obs = dados.desfecho_obs
    at.retorno_data = dados.retorno_data
    at.status = "FINALIZADO"
    at.fim_atendimento = datetime.now(timezone.utc)
    at.assinado = True
    at.assinado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(at)
    return at
