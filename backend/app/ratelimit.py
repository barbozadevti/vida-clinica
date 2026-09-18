"""Proteção simples contra força bruta no login — nenhum dos dois logins do
sistema (equipe por e-mail/senha, paciente por CPF/nascimento) tinha
qualquer limite de tentativas, o que é uma falha clássica de autenticação
(OWASP A07:2021) especialmente sensível aqui: o login do portal usa CPF, que
não é segredo, e data de nascimento, de baixa entropia.

Guarda o contador em memória (processo único, sem Redis) — suficiente para
este app, que roda como uma instância só; um deploy com múltiplos processos
precisaria de um armazenamento compartilhado."""
import time
from collections import defaultdict

from fastapi import HTTPException

_JANELA_SEG = 15 * 60
_MAX_TENTATIVAS = 5

_falhas: dict[str, list[float]] = defaultdict(list)


def _recentes(chave: str) -> list[float]:
    agora = time.time()
    vivas = [t for t in _falhas[chave] if agora - t < _JANELA_SEG]
    _falhas[chave] = vivas
    return vivas


def checar_bloqueio(*chaves: str) -> None:
    for chave in chaves:
        if len(_recentes(chave)) >= _MAX_TENTATIVAS:
            raise HTTPException(429, "Muitas tentativas. Aguarde alguns minutos e tente novamente.")


def registrar_falha(*chaves: str) -> None:
    for chave in chaves:
        _recentes(chave)
        _falhas[chave].append(time.time())


def limpar(*chaves: str) -> None:
    for chave in chaves:
        _falhas.pop(chave, None)
