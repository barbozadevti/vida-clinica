"""Log de auditoria (LGPD): rastreabilidade de quem acessou/alterou dado
sensível de saúde — objetivo já previsto na visão do produto, mas que até
aqui só existia como login+JWT, sem registro de acesso propriamente dito.
"""
from sqlalchemy.orm import Session

from .models import LogAcesso, Usuario


def registrar(
    db: Session,
    usuario: Usuario | None,
    acao: str,
    *,
    cidadao_id=None,
    atendimento_id=None,
    detalhe: str | None = None,
) -> None:
    """Grava uma linha de auditoria em commit isolado — chamado sempre DEPOIS
    do commit da ação principal do endpoint, para que uma falha ao gravar o
    log nunca derrube a ação clínica/financeira em si."""
    try:
        db.add(LogAcesso(
            usuario_id=usuario.id if usuario else None,
            acao=acao,
            cidadao_id=cidadao_id,
            atendimento_id=atendimento_id,
            detalhe=detalhe,
        ))
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[auditoria] falha ao registrar '{acao}': {exc}")
