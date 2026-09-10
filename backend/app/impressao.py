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


def _cabecalho() -> str:
    return f"""<table class="cab"><tr>
      <td style="width:14mm;font-size:20pt;text-align:center">✚</td>
      <td><span class="tit">{_e(settings.ubs_nome)}</span><br>
      <span class="sub">{_e(settings.ubs_linha2)} — {_e(settings.ubs_endereco)}</span></td>
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
    {_cabecalho()}<h2 class="doc">{_e(titulo)}</h2>{corpo}{_rodape(at)}{ap}</body></html>"""


def _caixa(titulo, conteudo, cls="") -> str:
    return f'<table class="box"><tr><td class="{cls}"><span class="lbl">{_e(titulo)}</span>{conteudo}</td></tr></table>'


# ─────────────────────────────────────────────────────────────
def render(tipo: str, at: Atendimento, autoprint: bool = True) -> str:
    tipo = tipo.lower()

    if tipo == "receita":
        if not at.prescricoes:
            raise ValueError("Nenhum medicamento prescrito neste atendimento")
        itens = "".join(
            f'<li><b>{_e(p.medicamento)}</b> — {_e(p.posologia)}'
            + (f' — <i>{_e(p.quantidade)}</i>' if p.quantidade else "")
            + (" <b>(uso contínuo)</b>" if p.uso_continuo else "")
            + (f'<br><span class="small">{_e(p.observacao)}</span>' if p.observacao else "")
            + "</li>"
            for p in at.prescricoes)
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
