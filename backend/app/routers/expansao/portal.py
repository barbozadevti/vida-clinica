"""Onda 4 (Lean Inception) — portal do paciente: acesso somente-leitura aos
próprios agendamentos e documentos, sem senha — autenticado por CPF + data
de nascimento. MVP para validar a hipótese; um portal de produção trocaria
essa autenticação por SMS/e-mail com código de uso único."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import ratelimit
from ...database import get_db
from ...impressao import render_pdf
from ...models import Agendamento, Atendimento, Cidadao
from ...schemas import (
    PortalAtendimentoOut,
    PortalLoginIn,
    PortalMeuPainelOut,
    PortalTokenOut,
)
from ...security import criar_token_portal, paciente_atual
from ...util import cidadao_dict, com_vitais

router = APIRouter(prefix="/api/portal", tags=["portal do paciente"])


def _so_digitos(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


@router.post("/entrar", response_model=PortalTokenOut)
def entrar(dados: PortalLoginIn, request: Request, db: Session = Depends(get_db)):
    cpf = _so_digitos(dados.cpf)
    # CPF não é segredo e data de nascimento tem pouca entropia — sem limite
    # de tentativas, dava pra "adivinhar" o nascimento de um CPF conhecido.
    chave_cpf = f"portal:{cpf}"
    chave_ip = f"portal-ip:{request.client.host if request.client else '?'}"
    ratelimit.checar_bloqueio(chave_cpf, chave_ip)
    cidadao = db.scalar(select(Cidadao).where(Cidadao.cpf == cpf)) if cpf else None
    if not cidadao or cidadao.data_nascimento != dados.data_nascimento:
        ratelimit.registrar_falha(chave_cpf, chave_ip)
        raise HTTPException(401, "CPF ou data de nascimento não conferem")
    ratelimit.limpar(chave_cpf, chave_ip)
    return PortalTokenOut(access_token=criar_token_portal(cidadao), paciente=cidadao)


@router.get("/mim", response_model=PortalMeuPainelOut)
def meu_painel(paciente: Cidadao = Depends(paciente_atual), db: Session = Depends(get_db)):
    hoje = date.today()
    agendamentos = db.scalars(
        select(Agendamento).where(
            Agendamento.cidadao_id == paciente.id,
            Agendamento.data >= hoje,
            Agendamento.status.notin_(["CANCELADO", "FALTOU"]),
        ).order_by(Agendamento.data, Agendamento.hora)
    ).all()
    atendimentos = db.scalars(
        select(Atendimento).where(
            Atendimento.cidadao_id == paciente.id,
            Atendimento.status == "FINALIZADO",
        ).order_by(Atendimento.fim_atendimento.desc()).limit(20)
    ).all()
    return PortalMeuPainelOut(
        paciente=cidadao_dict(paciente),
        proximos_agendamentos=agendamentos,
        atendimentos_anteriores=[
            PortalAtendimentoOut(
                id=a.id, criado_em=a.criado_em, fim_atendimento=a.fim_atendimento,
                desfecho=a.desfecho, profissional=a.profissional,
                tem_receita=bool(a.prescricoes), tem_atestado=bool(a.atestados),
                tem_exames=bool(a.solicitacoes_exame),
            )
            for a in atendimentos
        ],
    )


@router.get("/atendimentos/{aid}/pdf/{tipo}")
def documento(aid: str, tipo: str, paciente: Cidadao = Depends(paciente_atual),
              db: Session = Depends(get_db)):
    at = db.get(Atendimento, aid)
    if not at or str(at.cidadao_id) != str(paciente.id):
        raise HTTPException(404, "Documento não encontrado")
    com_vitais(db, at)
    try:
        pdf = render_pdf(tipo, at)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{tipo}.pdf"'})
