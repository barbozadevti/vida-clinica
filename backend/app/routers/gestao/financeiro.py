from datetime import date as date_cls, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...database import get_db
from ...impressao import render_guia_tiss, render_guia_tiss_pdf, render_nota_fiscal, render_nota_fiscal_pdf
from ...models import Cidadao, Cobranca, Usuario
from ...schemas import CobrancaIn, CobrancaOut, FinanceiroResumoOut
from ...security import exigir_perfis, usuario_atual

router = APIRouter(prefix="/api/financeiro", tags=["financeiro"])
_GESTAO = exigir_perfis("ADMIN", "RECEPCAO")

FORMAS_PAGAMENTO = {"DINHEIRO", "PIX", "CARTAO_DEBITO", "CARTAO_CREDITO", "CONVENIO", "BOLETO"}


@router.get("/formas-pagamento")
def formas_pagamento():
    return sorted(FORMAS_PAGAMENTO)


@router.get("/cobrancas", response_model=list[CobrancaOut])
def listar(status: str | None = None, de: date_cls | None = None, ate: date_cls | None = None,
           _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    stmt = select(Cobranca).order_by(Cobranca.criado_em.desc()).limit(300)
    if status:
        stmt = stmt.where(Cobranca.status == status.upper())
    if de:
        stmt = stmt.where(func.date(Cobranca.criado_em) >= de)
    if ate:
        stmt = stmt.where(func.date(Cobranca.criado_em) <= ate)
    return db.scalars(stmt).all()


@router.post("/cobrancas", response_model=CobrancaOut, status_code=201)
def criar(dados: CobrancaIn, usuario: Usuario = Depends(_GESTAO), db: Session = Depends(get_db)):
    if not db.get(Cidadao, dados.cidadao_id):
        raise HTTPException(400, "Cidadão inexistente")
    forma = dados.forma_pagamento.upper()
    if forma not in FORMAS_PAGAMENTO:
        raise HTTPException(400, f"Forma de pagamento inválida: {sorted(FORMAS_PAGAMENTO)}")
    if forma == "CONVENIO" and not dados.convenio_id:
        raise HTTPException(400, "Informe o convênio")
    payload = dados.model_dump()
    payload["forma_pagamento"] = forma
    c = Cobranca(**payload, criado_por_id=usuario.id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.post("/cobrancas/{cid}/pagar", response_model=CobrancaOut)
def pagar(cid: str, _: Usuario = Depends(_GESTAO), db: Session = Depends(get_db)):
    c = db.get(Cobranca, cid)
    if not c:
        raise HTTPException(404, "Cobrança não encontrada")
    if c.status != "PENDENTE":
        raise HTTPException(409, "Cobrança não está pendente")
    c.status = "PAGO"
    c.pago_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


@router.post("/cobrancas/{cid}/cancelar", response_model=CobrancaOut)
def cancelar(cid: str, _: Usuario = Depends(_GESTAO), db: Session = Depends(get_db)):
    c = db.get(Cobranca, cid)
    if not c:
        raise HTTPException(404, "Cobrança não encontrada")
    c.status = "CANCELADO"
    db.commit()
    db.refresh(c)
    return c


@router.get("/resumo", response_model=FinanceiroResumoOut)
def resumo(de: date_cls = Query(...), ate: date_cls = Query(...),
           _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    itens = db.scalars(select(Cobranca).where(
        func.date(Cobranca.criado_em) >= de, func.date(Cobranca.criado_em) <= ate,
        Cobranca.status != "CANCELADO",
    )).all()
    total_faturado = sum(c.valor for c in itens)
    total_pago = sum(c.valor for c in itens if c.status == "PAGO")
    por_forma: dict[str, float] = {}
    for c in itens:
        por_forma[c.forma_pagamento] = por_forma.get(c.forma_pagamento, 0) + c.valor
    return FinanceiroResumoOut(
        periodo_de=de, periodo_ate=ate,
        total_faturado=round(total_faturado, 2), total_pago=round(total_pago, 2),
        total_pendente=round(total_faturado - total_pago, 2),
        por_forma=[{"forma": k, "total": round(v, 2)} for k, v in sorted(por_forma.items(), key=lambda x: -x[1])],
    )


def _obter_ou_emitir_nf(db: Session, c: Cobranca) -> Cobranca:
    """Por lei, todo procedimento/consulta da clínica precisa de nota fiscal
    (não pode mais ser só recibo) — PF ou PJ. O número é sequencial e
    atribuído uma única vez, na primeira emissão; reimpressões reusam o
    mesmo número em vez de gerar um novo a cada clique."""
    if c.status == "CANCELADO":
        raise HTTPException(409, "Cobrança cancelada não pode emitir nota fiscal")
    if not c.numero_nf:
        seq = db.scalar(select(func.count()).select_from(Cobranca).where(Cobranca.numero_nf.isnot(None))) + 1
        c.numero_nf = f"{datetime.now(timezone.utc).year}/{seq:06d}"
        c.nf_emitida_em = datetime.now(timezone.utc)
        db.commit()
        db.refresh(c)
    return c


@router.get("/cobrancas/{cid}/nota-fiscal")
def nota_fiscal_html(cid: str, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    c = db.get(Cobranca, cid)
    if not c:
        raise HTTPException(404, "Cobrança não encontrada")
    c = _obter_ou_emitir_nf(db, c)
    return {"html": render_nota_fiscal(c)}


@router.get("/cobrancas/{cid}/nota-fiscal.pdf")
def nota_fiscal_pdf(cid: str, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    c = db.get(Cobranca, cid)
    if not c:
        raise HTTPException(404, "Cobrança não encontrada")
    c = _obter_ou_emitir_nf(db, c)
    pdf = render_nota_fiscal_pdf(c)
    nome = f"nota_fiscal_{c.numero_nf.replace('/', '-')}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})


@router.get("/cobrancas/{cid}/guia-tiss.pdf")
def guia_tiss_pdf(cid: str, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    c = db.get(Cobranca, cid)
    if not c:
        raise HTTPException(404, "Cobrança não encontrada")
    try:
        pdf = render_guia_tiss_pdf(c)
    except ValueError as e:
        raise HTTPException(400, str(e))
    nome = f"guia_tiss_{(c.cidadao.nome_completo or 'guia').split()[0].lower()}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})
