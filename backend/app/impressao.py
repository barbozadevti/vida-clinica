"""HTML (A4) e PDF dos documentos do atendimento — formulários no padrão SUS.

O HTML usa layout com tabelas para renderizar igual no navegador (window.print)
e no gerador de PDF (xhtml2pdf).
"""
import io
from datetime import datetime

from .config import settings
from .models import Atendimento

_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]

_TIPO_ENC = {
    "CONSULTA_ESPECIALIZADA": "Consulta com especialista",
    "AVALIACAO_CIRURGICA": "Avaliação / procedimento cirúrgico",
    "EXAMES_ESPECIALIZADOS": "Exames especializados",
    "URGENCIA": "Urgência / emergência",
    "OUTRO": "Outro",
}

_CSS = """
@page { size: A4; margin: 14mm 13mm; }
body { font-family: Helvetica, Arial, sans-serif; color: #000; font-size: 10.5pt; line-height: 1.35; }
.cab td { border: none; }
.cab .tit { font-size: 11pt; font-weight: bold; text-transform: uppercase; }
.cab .sub { font-size: 9pt; }
h2.doc { text-align: center; font-size: 12pt; margin: 10px 0 8px; text-transform: uppercase; letter-spacing: .5px; }
table { width: 100%; border-collapse: collapse; }
.box td { border: 1px solid #000; padding: 4px 6px; vertical-align: top; }
.lbl { font-size: 7.5pt; text-transform: uppercase; color: #333; display: block; }
.val { font-size: 10.5pt; }
.area { min-height: 60px; }
.area-lg { min-height: 150px; }
ol, ul { margin: 4px 0 4px 16px; padding: 0; }
li { margin-bottom: 4px; }
.assinatura { margin-top: 40px; text-align: center; }
.linha { border-top: 1px solid #000; width: 62mm; margin: 34px auto 3px; }
.data { text-align: right; margin-top: 14px; font-size: 9.5pt; }
.small { font-size: 8.5pt; color: #333; }
"""


def _e(s) -> str:
    s = "" if s is None else str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _hoje_cidade() -> str:
    d = datetime.now()
    cidade = settings.ubs_linha2.replace("Secretaria Municipal de Saúde", "").strip(" -") or "Município"
    return f"{d.day} de {_MESES[d.month - 1]} de {d.year}"


def _cabecalho(unidade=None) -> str:
    """Multiclínica: quando o atendimento tem uma Unidade vinculada, o
    cabeçalho impresso usa o nome/endereço dela em vez do dado global da
    configuração — cada unidade emite documento com seu próprio timbre."""
    nome = unidade.nome if unidade else settings.ubs_nome
    endereco = unidade.endereco if unidade and unidade.endereco else settings.ubs_endereco
    linha2 = settings.ubs_linha2 if not unidade else (unidade.telefone or settings.ubs_linha2)
    return f"""<table class="cab"><tr>
      <td style="width:14mm;font-size:20pt;text-align:center">✚</td>
      <td><span class="tit">{_e(nome)}</span><br>
      <span class="sub">{_e(linha2)} — {_e(endereco)}</span></td>
    </tr></table><hr>"""


def _ident(at: Atendimento, incluir_mae=True) -> str:
    c = at.cidadao
    nasc = c.data_nascimento.strftime("%d/%m/%Y") if c.data_nascimento else "—"
    idade = ""
    if c.data_nascimento:
        h = datetime.now().date()
        idade = f" ({h.year - c.data_nascimento.year - ((h.month, h.day) < (c.data_nascimento.month, c.data_nascimento.day))} anos)"
    linha_mae = (f'<tr><td colspan="3"><span class="lbl">Nome da mãe</span>'
                 f'<span class="val">{_e(c.nome_mae or "—")}</span></td></tr>' if incluir_mae else "")
    return f"""<table class="box"><tr>
      <td colspan="3"><span class="lbl">Nome do paciente</span>
        <span class="val">{_e(c.nome_social or c.nome_completo)}</span></td></tr>
      <tr>
        <td style="width:40%"><span class="lbl">Data de nascimento</span><span class="val">{nasc}{idade}</span></td>
        <td style="width:30%"><span class="lbl">Sexo</span><span class="val">{_e(c.sexo or "—")}</span></td>
        <td style="width:30%"><span class="lbl">Nº do Cartão SUS (CNS)</span><span class="val">{_e(c.cns or "—")}</span></td>
      </tr>
      <tr>
        <td><span class="lbl">CPF</span><span class="val">{_e(c.cpf or "—")}</span></td>
        <td colspan="2"><span class="lbl">Telefone</span><span class="val">{_e(c.telefone or "—")}</span></td>
      </tr>{linha_mae}</table>"""


def _rodape(at: Atendimento, extra_prof="") -> str:
    p = at.profissional
    return f"""<div class="data">{_e(_hoje_cidade())}</div>
    <div class="assinatura">
      <div class="linha"></div>
      <b>{_e(p.nome if p else "")}</b><br>
      <span class="small">{_e(p.conselho if p and p.conselho else "")}
      {(" · CBO " + _e(p.cbo)) if p and p.cbo else ""}
      {(" · CNS " + _e(p.cns)) if p and p.cns else ""}{extra_prof}</span>
    </div>"""


def _pagina(titulo, corpo, at, autoprint=True) -> str:
    ap = ("<script>window.onload=function(){setTimeout(function(){window.print()},250)}</script>"
          if autoprint else "")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
    <title>{_e(titulo)}</title><style>{_CSS}</style></head><body>
    {_cabecalho(at.unidade)}<h2 class="doc">{_e(titulo)}</h2>{corpo}{_rodape(at)}{ap}</body></html>"""


def _caixa(titulo, conteudo, cls="") -> str:
    return f'<table class="box"><tr><td class="{cls}"><span class="lbl">{_e(titulo)}</span>{conteudo}</td></tr></table>'


# ─────────────────────────────────────────────────────────────
def render(tipo: str, at: Atendimento, autoprint: bool = True) -> str:
    tipo = tipo.lower()

    if tipo in ("receita", "receita-simples", "receita-controle"):
        # Onda de correções: receita simples e receita de controle especial
        # (Portaria SVS/MS 344/98 — psicotrópicos, entorpecentes etc.) não
        # podem sair no mesmo papel; por isso viraram documentos separados.
        # "receita" (sem sufixo) é mantido por compatibilidade e imprime tudo
        # junto, como antes.
        if tipo == "receita-simples":
            itens_p = [p for p in at.prescricoes if not p.controle_especial]
        elif tipo == "receita-controle":
            itens_p = [p for p in at.prescricoes if p.controle_especial]
        else:
            itens_p = list(at.prescricoes)
        if not itens_p:
            raise ValueError("Nenhum medicamento prescrito nessa categoria")
        itens = "".join(
            f'<li><b>{_e(p.medicamento)}</b> — {_e(p.posologia)}'
            + (f' — <i>{_e(p.quantidade)}</i>' if p.quantidade else "")
            + (" <b>(uso contínuo)</b>" if p.uso_continuo else "")
            + (f'<br><span class="small">{_e(p.observacao)}</span>' if p.observacao else "")
            + "</li>"
            for p in itens_p)
        if tipo == "receita-controle":
            corpo = (
                '<p style="text-align:center;font-weight:bold;margin:0 0 10px">'
                'RECEITUÁRIO DE CONTROLE ESPECIAL — 2 VIAS (Portaria SVS/MS 344/98)</p>'
                + _ident(at, incluir_mae=False)
                + _caixa("Prescrição", f"<ol>{itens}</ol>", "area-lg")
                + '<p class="small" style="margin-top:8px">1ª via — Farmácia &nbsp;|&nbsp; 2ª via — Paciente</p>'
            )
            return _pagina("Receituário de Controle Especial", corpo, at, autoprint)
        corpo = _ident(at, incluir_mae=False) + _caixa("Prescrição", f"<ol>{itens}</ol>", "area-lg")
        return _pagina("Receituário", corpo, at, autoprint)

    if tipo == "atestado":
        if not at.atestados:
            raise ValueError("Nenhum atestado emitido neste atendimento")
        a = at.atestados[-1]
        texto = _e(a.texto).replace("\n", "<br>")
        corpo = (_ident(at, incluir_mae=False)
                 + _caixa("", f'<p class="val">{texto}</p>', "area-lg"))
        return _pagina("Atestado Médico", corpo, at, autoprint)

    if tipo == "exames":
        if not at.solicitacoes_exame:
            raise ValueError("Nenhuma solicitação de exame neste atendimento")
        s = at.solicitacoes_exame[-1]
        linhas = "".join(f"<li>{_e(x)}</li>" for x in s.exames.splitlines() if x.strip())
        cids = "; ".join(dict.fromkeys(f"{_e(p.codigo)} {_e(p.descricao)}" for p in at.problemas)) or "—"
        corpo = (_ident(at)
                 + f"""<table class="box"><tr>
                     <td style="width:50%"><span class="lbl">Caráter do atendimento</span>
                       <span class="val">{"URGENTE" if s.prioridade == "URGENTE" else "ELETIVO / ROTINA"}</span></td>
                     <td><span class="lbl">CID / CIAP relacionado</span><span class="val">{cids}</span></td>
                   </tr></table>"""
                 + _caixa("Exames / procedimentos solicitados", f"<ol>{linhas}</ol>", "area-lg")
                 + _caixa("Indicação clínica / justificativa",
                          f'<p class="val">{_e(s.indicacao_clinica or at.avaliacao or "—")}</p>', "area"))
        return _pagina("Requisição de Exames — SUS", corpo, at, autoprint)

    if tipo == "encaminhamento":
        if not at.encaminhamentos:
            raise ValueError("Nenhum encaminhamento neste atendimento")
        e = at.encaminhamentos[-1]
        cid = e.cid or "; ".join(dict.fromkeys(f"{_e(p.codigo)} {_e(p.descricao)}" for p in at.problemas)) or "—"
        vitais = ", ".join(f"{k.replace('_', ' ').title()}: {v}"
                           for k, v in (at.vitais_acolhimento or {}).items()) or "—"
        corpo = (_ident(at)
                 + f"""<table class="box"><tr>
                     <td style="width:34%"><span class="lbl">Tipo de encaminhamento</span>
                       <span class="val">{_e(_TIPO_ENC.get(e.tipo, e.tipo))}</span></td>
                     <td style="width:33%"><span class="lbl">Especialidade / serviço de destino</span>
                       <span class="val">{_e(e.especialidade)}</span></td>
                     <td><span class="lbl">Prioridade</span><span class="val">{_e(e.prioridade)}</span></td>
                   </tr>
                   <tr><td colspan="3"><span class="lbl">CID</span><span class="val">{cid}</span></td></tr>
                   </table>"""
                 + _caixa("Motivo do encaminhamento / resumo clínico", f'<p class="val">{_e(e.motivo)}</p>', "area")
                 + _caixa("História clínica (S) e avaliação (A)",
                          f'<p class="val">{_e((at.subjetivo or "—"))}<br><br>{_e(at.avaliacao or "")}</p>', "area")
                 + _caixa("Exame físico / sinais vitais (O)",
                          f'<p class="val">{_e(at.objetivo or "—")}<br><span class="small">{_e(vitais)}</span></p>', "area")
                 + _caixa("Conduta / medicações em uso (P)", f'<p class="val">{_e(at.plano or "—")}</p>', "area"))
        titulo = ("Guia de Encaminhamento para Avaliação Cirúrgica"
                  if e.tipo == "AVALIACAO_CIRURGICA" else "Guia de Encaminhamento — SUS")
        return _pagina(titulo, corpo, at, autoprint)

    if tipo == "resumo":
        probs = "".join(f"<li>{_e(p.sistema)} {_e(p.codigo)} — {_e(p.descricao)}</li>" for p in at.problemas)
        presc = "".join(f"<li>{_e(p.medicamento)} — {_e(p.posologia)}</li>" for p in at.prescricoes)
        corpo = (_ident(at, incluir_mae=False)
                 + _caixa("S — Subjetivo", f'<p class="val">{_e(at.subjetivo or "—")}</p>', "area")
                 + _caixa("O — Objetivo", f'<p class="val">{_e(at.objetivo or "—")}</p>', "area")
                 + _caixa("A — Avaliação",
                          (f"<ul>{probs}</ul>" if probs else "") + f'<p class="val">{_e(at.avaliacao or "")}</p>', "area")
                 + _caixa("P — Plano", f'<p class="val">{_e(at.plano or "—")}</p>', "area")
                 + (_caixa("Prescrição", f"<ul>{presc}</ul>") if presc else "")
                 + _caixa("Desfecho",
                          f'<span class="val">{_e((at.desfecho or "—").replace("_", " "))}'
                          + (f' — retorno em {at.retorno_data.strftime("%d/%m/%Y")}' if at.retorno_data else "")
                          + "</span>"))
        return _pagina("Resumo do Atendimento", corpo, at, autoprint)

    raise ValueError("Tipo de documento inválido")


def render_pdf(tipo: str, at: Atendimento) -> bytes:
    from xhtml2pdf import pisa

    html = render(tipo, at, autoprint=False)
    out = io.BytesIO()
    res = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if res.err:
        raise ValueError("Falha ao gerar o PDF")
    return out.getvalue()


# ─────────────────────────────────────────────────────────────
# Recibo de pagamento (Financeiro) — não depende de Atendimento
def _valor_fmt(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _cnpj_fmt(v: str | None) -> str:
    if not v or len(v) != 14:
        return v or "—"
    return f"{v[0:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:14]}"


def _cpf_fmt(v: str | None) -> str:
    if not v or len(v) != 11:
        return v or "—"
    return f"{v[0:3]}.{v[3:6]}.{v[6:9]}-{v[9:11]}"


def _tomador_nf(c) -> str:
    """Define o tomador do serviço na nota fiscal: pessoa jurídica quando a
    cobrança é de convênio com CNPJ cadastrado, senão pessoa física (o
    próprio paciente, pelo CPF) — por lei toda consulta/procedimento emite
    nota fiscal, seja para PF ou PJ."""
    cid = c.cidadao
    if c.convenio and c.convenio.cnpj:
        return f"""<table class="box"><tr>
          <td><span class="lbl">Tomador do serviço (Pessoa Jurídica)</span>
            <span class="val">{_e(c.convenio.nome)}</span></td>
          <td style="width:35%"><span class="lbl">CNPJ</span><span class="val">{_cnpj_fmt(c.convenio.cnpj)}</span></td>
        </tr>
        <tr><td colspan="2"><span class="lbl">Paciente atendido</span>
          <span class="val">{_e(cid.nome_social or cid.nome_completo)}</span></td></tr></table>"""
    return f"""<table class="box"><tr>
      <td><span class="lbl">Tomador do serviço (Pessoa Física)</span>
        <span class="val">{_e(cid.nome_social or cid.nome_completo)}</span></td>
      <td style="width:35%"><span class="lbl">CPF</span><span class="val">{_cpf_fmt(cid.cpf)}</span></td>
    </tr></table>"""


def render_nota_fiscal(c, autoprint: bool = True) -> str:
    if not c.numero_nf:
        raise ValueError("Nota fiscal ainda não emitida para esta cobrança")
    unidade = c.atendimento.unidade if c.atendimento else None
    prestador_cnpj = (unidade.cnpj if unidade and unidade.cnpj else settings.ubs_cnpj)
    forma = c.forma_pagamento.replace("_", " ").title()
    emitida = c.nf_emitida_em.strftime("%d/%m/%Y %H:%M") if c.nf_emitida_em else "—"
    corpo = f"""{_tomador_nf(c)}
    <table class="box"><tr>
      <td style="width:34%"><span class="lbl">Valor do serviço</span><span class="val"><b>{_valor_fmt(c.valor)}</b></span></td>
      <td style="width:33%"><span class="lbl">Forma de pagamento</span><span class="val">{_e(forma)}</span></td>
      <td><span class="lbl">Situação</span><span class="val">{_e(c.status)}</span></td>
    </tr>
    <tr><td colspan="3"><span class="lbl">Discriminação do serviço</span><span class="val">{_e(c.descricao)}</span></td></tr>
    </table>"""
    ap = ("<script>window.onload=function(){setTimeout(function(){window.print()},250)}</script>"
          if autoprint else "")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
    <title>Nota Fiscal de Serviço {_e(c.numero_nf)}</title><style>{_CSS}</style></head><body>
    {_cabecalho(unidade)}
    <table class="box"><tr>
      <td><span class="lbl">CNPJ do prestador</span><span class="val">{_cnpj_fmt(prestador_cnpj)}</span></td>
      <td style="width:35%"><span class="lbl">Nº da nota fiscal</span><span class="val"><b>{_e(c.numero_nf)}</b></span></td>
    </tr></table>
    <h2 class="doc">Nota Fiscal de Serviço (simplificada)</h2>{corpo}
    <p class="small" style="margin-top:8px">Documento interno simplificado, gerado pelo setor financeiro/recepção —
    controla numeração sequencial e os dados do tomador (PF/PJ) exigidos por lei, mas não substitui a NFS-e eletrônica
    oficial. A emissão fiscal de verdade é feita à parte, no portal da Secretaria Municipal da Fazenda do município
    (ou por um sistema de nota fiscal eletrônica integrado a ele) e fica fora do escopo deste sistema de
    demonstração.</p>
    <div class="data">Emitida em {emitida}</div>
    <div class="assinatura"><div class="linha"></div><b>{_e(unidade.nome if unidade else settings.ubs_nome)}</b></div>
    {ap}</body></html>"""


def render_nota_fiscal_pdf(c) -> bytes:
    from xhtml2pdf import pisa

    html = render_nota_fiscal(c, autoprint=False)
    out = io.BytesIO()
    res = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if res.err:
        raise ValueError("Falha ao gerar o PDF")
    return out.getvalue()


# ─────────────────────────────────────────────────────────────
# Guia TISS simplificada (Financeiro/Onda 5) — não depende de Atendimento.
# Reúne os campos mínimos de uma guia de consulta TISS (padrão da ANS) para
# validar a hipótese; não é o XML SADT/consulta que a ANS exige para envio
# eletrônico à operadora — isso fica para uma próxima onda.
def render_guia_tiss(c, autoprint: bool = True) -> str:
    if not c.convenio:
        raise ValueError("Esta cobrança não tem convênio associado")
    cid = c.cidadao
    at = c.atendimento
    prof = at.profissional if at else None
    cids = "; ".join(dict.fromkeys(f"{_e(p.codigo)} {_e(p.descricao)}" for p in at.problemas)) if at else "—"
    nasc = cid.data_nascimento.strftime("%d/%m/%Y") if cid.data_nascimento else "—"
    corpo = f"""<table class="box"><tr>
        <td><span class="lbl">Operadora</span><span class="val">{_e(c.convenio.nome)}</span></td>
        <td style="width:30%"><span class="lbl">Registro ANS</span><span class="val">{_e(c.convenio.registro_ans or "—")}</span></td>
      </tr></table>
      <table class="box"><tr>
        <td colspan="2"><span class="lbl">Beneficiário</span><span class="val">{_e(cid.nome_social or cid.nome_completo)}</span></td></tr>
      <tr>
        <td><span class="lbl">Nº da carteirinha</span><span class="val">{_e(cid.numero_carteirinha or "—")}</span></td>
        <td><span class="lbl">Nascimento</span><span class="val">{nasc}</span></td>
      </tr></table>
      <table class="box"><tr>
        <td><span class="lbl">Profissional executante</span><span class="val">{_e(prof.nome if prof else "—")}</span></td>
        <td style="width:30%"><span class="lbl">Conselho / CBO</span><span class="val">{_e(prof.conselho or "—") if prof else "—"}{(" / " + _e(prof.cbo)) if prof and prof.cbo else ""}</span></td>
      </tr></table>
      <table class="box"><tr>
        <td style="width:25%"><span class="lbl">Código do procedimento (TUSS)</span><span class="val">{_e(c.codigo_tuss or "—")}</span></td>
        <td><span class="lbl">Procedimento / descrição</span><span class="val">{_e(c.descricao)}</span></td>
      </tr>
      <tr><td colspan="2"><span class="lbl">CID relacionado</span><span class="val">{cids}</span></td></tr>
      <tr>
        <td><span class="lbl">Data do atendimento</span><span class="val">{_e(c.criado_em.strftime("%d/%m/%Y"))}</span></td>
        <td><span class="lbl">Valor</span><span class="val"><b>{_valor_fmt(c.valor)}</b></span></td>
      </tr></table>"""
    ap = ("<script>window.onload=function(){setTimeout(function(){window.print()},250)}</script>"
          if autoprint else "")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
    <title>Guia TISS — Simplificada</title><style>{_CSS}</style></head><body>
    {_cabecalho()}<h2 class="doc">Guia TISS — Consulta (simplificada)</h2>{corpo}
    <p class="small" style="margin-top:8px">Documento interno simplificado, não substitui a guia eletrônica TISS exigida
    para faturamento junto à operadora.</p>
    <div class="data">{_e(_hoje_cidade())}</div>
    {ap}</body></html>"""


def render_guia_tiss_pdf(c) -> bytes:
    from xhtml2pdf import pisa

    html = render_guia_tiss(c, autoprint=False)
    out = io.BytesIO()
    res = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if res.err:
        raise ValueError("Falha ao gerar o PDF")
    return out.getvalue()


# ─────────────────────────────────────────────────────────────
# Relatório de produção (Relatórios) — não depende de Atendimento
def _tabela_relatorio(titulo: str, linhas: list[dict], colunas: list[tuple]) -> str:
    """colunas: lista de (chave, rótulo) — a última coluna vira <b>."""
    if not linhas:
        return _caixa(titulo, '<p class="small">Sem dados no período.</p>')
    cab = "".join(f"<td><b>{_e(l)}</b></td>" for _, l in colunas)
    corpo = "".join(
        "<tr>" + "".join(
            f"<td>{_e(r.get(k, '—'))}</td>" if i < len(colunas) - 1
            else f"<td><b>{_e(r.get(k, '—'))}</b></td>"
            for i, (k, _) in enumerate(colunas)
        ) + "</tr>"
        for r in linhas
    )
    tabela = f'<table class="box"><tr>{cab}</tr>{corpo}</table>'
    return f'<div style="margin-top:8px"><span class="lbl">{_e(titulo)}</span></div>{tabela}'


def render_producao(dados: dict, autoprint: bool = True) -> str:
    periodo = f"{dados['periodo_de'].strftime('%d/%m/%Y')} a {dados['periodo_ate'].strftime('%d/%m/%Y')}"
    corpo = f"""<table class="box"><tr>
        <td><span class="lbl">Período</span><span class="val">{_e(periodo)}</span></td>
        <td><span class="lbl">Atendimentos finalizados</span><span class="val"><b>{dados['total']}</b></span></td>
      </tr></table>"""
    corpo += _tabela_relatorio("Por profissional", dados["por_profissional"],
                               [("nome", "Profissional"), ("total", "Total")])
    corpo += _tabela_relatorio("Por desfecho",
                               [{"nome": r["nome"].replace("_", " "), "total": r["total"]} for r in dados["por_desfecho"]],
                               [("nome", "Desfecho"), ("total", "Total")])
    corpo += _tabela_relatorio("Por classificação de risco", dados["por_risco"],
                               [("nome", "Risco"), ("total", "Total")])
    corpo += _tabela_relatorio("CID/CIAP mais frequentes", dados["por_cid"],
                               [("codigo", "Código"), ("descricao", "Descrição"), ("total", "Total")])
    ap = ("<script>window.onload=function(){setTimeout(function(){window.print()},250)}</script>"
          if autoprint else "")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
    <title>Relatório de Produção</title><style>{_CSS}</style></head><body>
    {_cabecalho()}<h2 class="doc">Relatório de Produção</h2>{corpo}
    <div class="data">{_e(_hoje_cidade())}</div>
    {ap}</body></html>"""


def render_producao_pdf(dados: dict) -> bytes:
    from xhtml2pdf import pisa

    html = render_producao(dados, autoprint=False)
    out = io.BytesIO()
    res = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if res.err:
        raise ValueError("Falha ao gerar o PDF")
    return out.getvalue()
