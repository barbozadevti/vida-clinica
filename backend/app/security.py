from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Cidadao, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

PERFIS = {"ADMIN", "MEDICO", "ENFERMEIRO", "RECEPCAO"}


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8")[:72], senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def criar_token(usuario: Usuario) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id),
        "perfil": usuario.perfil,
        "nome": usuario.nome,
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.jwt_expires_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def usuario_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise exc
    usuario = db.get(Usuario, user_id)
    if usuario is None or not usuario.ativo:
        raise exc
    return usuario


# ─────────── Portal do paciente ───────────
# Token separado do login da equipe (escopo "portal"): não usa perfil nem
# senha — a autenticação é CPF + data de nascimento (ver routers/expansao/portal.py).
# Suficiente para validar a hipótese do MVP; um portal real de produção
# trocaria isso por SMS/e-mail com código de uso único.
_PORTAL_EXPIRES_MIN = 60


def criar_token_portal(cidadao: Cidadao) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(cidadao.id),
        "scope": "portal",
        "iat": agora,
        "exp": agora + timedelta(minutes=_PORTAL_EXPIRES_MIN),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def paciente_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Cidadao:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão do portal inválida ou expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("scope") != "portal":
            raise exc
        cidadao_id = payload.get("sub")
    except jwt.PyJWTError:
        raise exc
    cidadao = db.get(Cidadao, cidadao_id)
    if cidadao is None:
        raise exc
    return cidadao


def exigir_perfis(*perfis: str):
    def _guard(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.perfil != "ADMIN" and usuario.perfil not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso restrito: {', '.join(('ADMIN', *perfis))}",
            )
        return usuario

    return _guard
