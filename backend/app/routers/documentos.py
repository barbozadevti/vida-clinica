from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Atendimento,
    Atestado,
    MedicamentoEmUso,
    Prescricao,
    SolicitacaoExame,
    Usuario,
)
from ..schemas import (
    AtestadoIn,
    AtestadoOut,
    PrescricaoIn,
    PrescricaoOut,
    SolicitacaoExameIn,
    SolicitacaoExameOut,
)
from ..impressao import render as render_doc
from ..models import Usuario as _U
from ..security import exigir_perfis, usuario_atual

router = APIRouter(prefix="/api/atendimentos", tags=["documentos (Passo 4)"])
_CLINICO = exigir_perfis("MEDICO", "ENFERMEIRO")


def _atend_editavel(db: Session, aid: str, usuario: Usuario) -> Atendimento:
    at = db.get(Atendimento, aid)
    if not at:
        raise HTTPException(404, "Atendimento não encontrado")
    if at.assinado or at.status == "FINALIZADO":
        raise HTTPException(409, "Atendimento finalizado — documentos não podem ser alterados")
    if at.profissional_id and str(at.profissional_id) != str(usuario.id):
        raise HTTPException(403, "Atendimento sob responsabilidade de outro profissional")
    return at


# ─────────── Prescrição de medicamentos ───────────
@router.post("/{aid}/prescricoes", response_model=PrescricaoOut, status_code=201)
def prescrever(aid: str, dados: PrescricaoIn, usuario: Usuario = Depends(_CLINICO),
               db: Session = Depends(get_db)):
    at = _atend_editavel(db, aid, usuario)
    p = Prescricao(atendimento_id=at.id, **dados.model_dump())
    db.add(p)
    # uso contínuo entra na lista de medicamentos em uso do cidadão
    if dados.uso_continuo:
        db.add(MedicamentoEmUso(
            cidadao_id=at.cidadao_id, descricao=dados.medicamento,
            posologia=dados.posologia, via=dados.via, uso_continuo=True,
            inicio=date.today(), atendimento_id=at.id,
        ))
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{aid}/prescricoes/{pid}", status_code=204)
def remover_prescricao(aid: str, pid: str, usuario: Usuario = Depends(_CLINICO),
                       db: Session = Depends(get_db)):
    _atend_editavel(db, aid, usuario)
    p = db.get(Prescricao, pid)
    if not p or str(p.atendimento_id) != aid:
        raise HTTPException(404, "Prescrição não encontrada")
    db.delete(p)
    db.commit()


# ─────────── Atestado médico ───────────
@router.post("/{aid}/atestados", response_model=AtestadoOut, status_code=201)
def emitir_atestado(aid: str, dados: AtestadoIn, usuario: Usuario = Depends(_CLINICO),
                    db: Session = Depends(get_db)):
    at = _atend_editavel(db, aid, usuario)
    texto = dados.texto
    if not texto:
        nome = at.cidadao.nome_social or at.cidadao.nome_completo
        di = (dados.data_inicio or date.today()).strftime("%d/%m/%Y")
        if dados.tipo.upper() == "AFASTAMENTO":
            d = dados.dias_afastamento or 1
            texto = (f"Atesto para os devidos fins que {nome} necessita de afastamento "
                     f"de suas atividades por {d} dia(s), a partir de {di}"
                     + (f", CID {dados.cid}." if dados.cid else "."))
        else:
            texto = (f"Atesto que {nome} esteve sob atendimento médico nesta "
                     f"unidade de saúde na data de {di}, no período da consulta.")
        texto += f"\n\n{usuario.nome} — {usuario.conselho or ''}"
    a = Atestado(
        atendimento_id=at.id, tipo=dados.tipo.upper(),
        dias_afastamento=dados.dias_afastamento, cid=dados.cid,
        data_inicio=dados.data_inicio or date.today(), texto=texto,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{aid}/atestados/{tid}", status_code=204)
def remover_atestado(aid: str, tid: str, usuario: Usuario = Depends(_CLINICO),
                     db: Session = Depends(get_db)):
    _atend_editavel(db, aid, usuario)
    a = db.get(Atestado, tid)
    if not a or str(a.atendimento_id) != aid:
        raise HTTPException(404, "Atestado não encontrado")
    db.delete(a)
    db.commit()


# ─────────── Solicitação de exames ───────────
@router.post("/{aid}/exames", response_model=SolicitacaoExameOut, status_code=201)
def solicitar_exames(aid: str, dados: SolicitacaoExameIn, usuario: Usuario = Depends(_CLINICO),
                     db: Session = Depends(get_db)):
    at = _atend_editavel(db, aid, usuario)
    s = SolicitacaoExame(
        atendimento_id=at.id, exames=dados.exames,
        indicacao_clinica=dados.indicacao_clinica,
        prioridade=(dados.prioridade or "ROTINA").upper(),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{aid}/exames/{sid}", status_code=204)
def remover_solicitacao(aid: str, sid: str, usuario: Usuario = Depends(_CLINICO),
                        db: Session = Depends(get_db)):
    _atend_editavel(db, aid, usuario)
    s = db.get(SolicitacaoExame, sid)
    if not s or str(s.atendimento_id) != aid:
        raise HTTPException(404, "Solicitação não encontrada")
    db.delete(s)
    db.commit()


# ─────────── Impressão (receita | atestado | exames) ───────────
@router.get("/{aid}/documento/{tipo}")
def documento_impressao(aid: str, tipo: str, _: _U = Depends(usuario_atual),
                        db: Session = Depends(get_db)):
    at = db.get(Atendimento, aid)
    if not at:
        raise HTTPException(404, "Atendimento não encontrado")
    try:
        return {"html": render_doc(tipo, at)}
    except ValueError as e:
        raise HTTPException(400, str(e))
