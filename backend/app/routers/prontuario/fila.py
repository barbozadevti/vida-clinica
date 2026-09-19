from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Atendimento, Cidadao, Medicao, Usuario
from ...schemas import AcolhimentoIn, AtendimentoOut, AtendimentoResumo, FilaIn, TrocarProfissionalIn
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
def listar_fila(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    """Lista de atendimento do dia: quem está AGUARDANDO ou EM_ATENDIMENTO.

    Multiclínica: quem não é ADMIN e tem unidade definida só vê a fila da
    própria unidade (atendimentos sem unidade definida — legado — continuam
    visíveis a todos, pra não sumir dado antigo)."""
    inicio_dia = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    stmt = select(Atendimento).where(
        Atendimento.status.in_(["AGUARDANDO", "EM_ATENDIMENTO"]),
        Atendimento.criado_em >= inicio_dia,
    )
    if usuario.perfil != "ADMIN" and usuario.unidade_id:
        stmt = stmt.where(Atendimento.unidade_id.in_([usuario.unidade_id, None]))
    itens = db.scalars(stmt).all()
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
    if dados.profissional_id and not db.scalar(
        select(Usuario).where(Usuario.id == dados.profissional_id, Usuario.perfil.in_(["MEDICO", "ENFERMEIRO"]))
    ):
        raise HTTPException(400, "Profissional inválido")
    at = Atendimento(
        cidadao_id=dados.cidadao_id,
        criado_por_id=usuario.id,
        unidade_id=usuario.unidade_id,
        status="AGUARDANDO",
        tipo=dados.tipo,
        motivo=dados.motivo,
        classificacao_risco=dados.classificacao_risco,
        profissional_id=dados.profissional_id,
    )
    db.add(at)
    db.commit()
    db.refresh(at)
    return at


@router.post("/{atendimento_id}/profissional", response_model=AtendimentoResumo)
def trocar_profissional(
    atendimento_id: str,
    dados: TrocarProfissionalIn,
    usuario: Usuario = Depends(exigir_perfis("RECEPCAO", "ENFERMEIRO")),
    db: Session = Depends(get_db),
):
    """"Trocar de médico" — define ou muda para qual profissional este
    atendimento da fila é direcionado, antes de alguém clicar Atender (ex.:
    o paciente pede pra ser visto pela Dra. Katia em vez do Dr. Victor)."""
    at = db.get(Atendimento, atendimento_id)
    if not at:
        raise HTTPException(404, "Atendimento não encontrado")
    if at.status != "AGUARDANDO":
        raise HTTPException(409, "Só é possível trocar o profissional enquanto aguarda atendimento")
    if dados.profissional_id and not db.scalar(
        select(Usuario).where(Usuario.id == dados.profissional_id, Usuario.perfil.in_(["MEDICO", "ENFERMEIRO"]))
    ):
        raise HTTPException(400, "Profissional inválido")
    at.profissional_id = dados.profissional_id
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
        # se alguém já direcionou esse atendimento para um profissional
        # específico ("trocar de médico"), só ele (ou o ADMIN) pode atender
        if (at.profissional_id and str(at.profissional_id) != str(usuario.id)
                and usuario.perfil != "ADMIN"):
            nome = at.profissional.nome if at.profissional else "outro profissional"
            raise HTTPException(409, f"Este atendimento foi direcionado para {nome}")
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
