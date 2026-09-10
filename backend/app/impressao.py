"""Geração de HTML para impressão de documentos do atendimento (A4)."""
from datetime import datetime

from .config import settings
from .models import Atendimento

_CSS = """
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', Arial, sans-serif; color: #111; margin: 0;
  padding: 24mm 20mm; font-size: 13px; line-height: 1.5; }
.cab { text-align: center; border-bottom: 2px solid #111; padding-bottom: 8px; margin-bottom: 16px; }
.cab h1 { font-size: 15px; margin: 0; text-transform: uppercase; }
.cab .l2 { font-size: 12px; }
.cab .end { font-size: 11px; color: #444; margin-top: 2px; }
.titulo { text-align: center; font-size: 15px; font-weight: bold; text-transform: uppercase;
  margin: 18px 0 14px; letter-spacing: 1px; }
.bloco-id { border: 1px solid #999; padding: 8px 10px; margin-bottom: 16px; font-size: 12px; }
.bloco-id b { display: inline-block; min-width: 90px; }
.corpo { min-height: 90mm; white-space: pre-wrap; }
.corpo ol { margin: 0; padding-left: 22px; }
.corpo li { margin-bottom: 10px; }
.rodape { margin-top: 40px; text-align: center; }
.assinatura { margin: 46px auto 4px; border-top: 1px solid #111; width: 65mm; }
.rodape .nome { font-weight: bold; }
.rodape .reg { font-size: 12px; color: #333; }
.data { text-align: right; margin-top: 24px; font-size: 12px; }
@media print { body { padding: 12mm 16mm; } @page { size: A4; margin: 0; } }
"""

_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _hoje_extenso() -> str:
    d = datetime.now()
    return f"{settings.ubs_nome.split('-')[0].strip()}, {d.day} de {_MESES[d.month - 1]} de {d.year}"


def _e(s) -> str:
    s = "" if s is None else str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _cabecalho() -> str:
    return (f'<div class="cab"><h1>{_e(settings.ubs_nome)}</h1>'
            f'<div class="l2">{_e(settings.ubs_linha2)}</div>'
            f'<div class="end">{_e(settings.ubs_endereco)}</div></div>')


def _identificacao(at: Atendimento) -> str:
    c = at.cidadao
    return (f'<div class="bloco-id">'
            f'<div><b>Paciente:</b> {_e(c.nome_social or c.nome_completo)}</div>'
            f'<div><b>Nascimento:</b> {c.data_nascimento.strftime("%d/%m/%Y") if c.data_nascimento else "-"}'
            f' &nbsp;&nbsp; <b>CNS:</b> {_e(c.cns or "-")}'
            f' &nbsp;&nbsp; <b>CPF:</b> {_e(c.cpf or "-")}</div>'
            f'</div>')


def _rodape(at: Atendimento) -> str:
    p = at.profissional
    nome = _e(p.nome if p else "")
    reg = _e(p.conselho if p and p.conselho else "")
    return (f'<div class="data">{_e(_hoje_extenso())}</div>'
            f'<div class="rodape"><div class="assinatura"></div>'
            f'<div class="nome">{nome}</div>'
            f'<div class="reg">{reg}</div></div>')


def _pagina(titulo: str, corpo_html: str, at: Atendimento) -> str:
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<title>{_e(titulo)}</title><style>{_CSS}</style></head><body>'
            f'{_cabecalho()}<div class="titulo">{_e(titulo)}</div>'
            f'{_identificacao(at)}<div class="corpo">{corpo_html}</div>'
            f'{_rodape(at)}'
            f'<script>window.onload=function(){{setTimeout(function(){{window.print()}},250)}}</script>'
            f'</body></html>')


def render(tipo: str, at: Atendimento) -> str:
    tipo = tipo.lower()
    if tipo == "receita":
        if not at.prescricoes:
            raise ValueError("Nenhum medicamento prescrito neste atendimento")
        itens = "".join(
            f'<li><b>{_e(p.medicamento)}</b><br>{_e(p.posologia)}'
            + (f' &mdash; {_e(p.quantidade)}' if p.quantidade else "")
            + (f'<br><i>Uso contínuo</i>' if p.uso_continuo else "")
            + (f'<br>{_e(p.observacao)}' if p.observacao else "")
            + "</li>"
            for p in at.prescricoes
        )
        return _pagina("Receituário", f"<ol>{itens}</ol>", at)

    if tipo == "atestado":
        if not at.atestados:
            raise ValueError("Nenhum atestado emitido neste atendimento")
        a = at.atestados[-1]
        return _pagina("Atestado Médico", _e(a.texto).replace("\n", "<br>"), at)

    if tipo == "exames":
        if not at.solicitacoes_exame:
            raise ValueError("Nenhuma solicitação de exame neste atendimento")
        s = at.solicitacoes_exame[-1]
        linhas = "".join(f"<li>{_e(x)}</li>" for x in s.exames.splitlines() if x.strip())
        extra = ""
        if s.indicacao_clinica:
            extra = f'<p><b>Indicação clínica:</b> {_e(s.indicacao_clinica)}</p>'
        prio = f'<p><b>Prioridade:</b> {_e(s.prioridade)}</p>'
        return _pagina("Solicitação de Exames", f"<ol>{linhas}</ol>{extra}{prio}", at)

    raise ValueError("Tipo de documento inválido")
