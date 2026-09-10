from datetime import date, datetime


def idade(nascimento: date | None) -> int | None:
    if not nascimento:
        return None
    hoje = date.today()
    return (
        hoje.year
        - nascimento.year
        - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
    )


def cidadao_dict(c) -> dict:
    """Serializa Cidadao acrescentando idade (para os *Out schemas)."""
    return {
        "id": c.id,
        "nome_completo": c.nome_completo,
        "nome_social": c.nome_social,
        "cpf": c.cpf,
        "cns": c.cns,
        "data_nascimento": c.data_nascimento,
        "sexo": c.sexo,
        "nome_mae": c.nome_mae,
        "telefone": c.telefone,
        "endereco": c.endereco,
        "criado_em": c.criado_em,
        "idade": idade(c.data_nascimento),
    }
