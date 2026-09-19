from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import auditoria, ratelimit
from ...database import get_db
from ...models import Usuario
from ...schemas import LoginIn, TokenOut, UsuarioResumo
from ...security import criar_token, usuario_atual, verificar_senha

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _autenticar(db: Session, request: Request, email: str, senha: str) -> Usuario:
    email = email.lower().strip()
    chave_email, chave_ip = f"login:{email}", f"login-ip:{request.client.host if request.client else '?'}"
    ratelimit.checar_bloqueio(chave_email, chave_ip)
    u = db.scalar(select(Usuario).where(Usuario.email == email))
    if not u or not verificar_senha(senha, u.senha_hash):
        ratelimit.registrar_falha(chave_email, chave_ip)
        raise HTTPException(401, "E-mail ou senha incorretos")
    if not u.ativo:
        raise HTTPException(403, "Usuário inativo")
    ratelimit.limpar(chave_email, chave_ip)
    auditoria.registrar(db, u, "LOGIN", detalhe=chave_ip.removeprefix("login-ip:"))
    return u


@router.post("/login", response_model=TokenOut)
def login(request: Request, dados: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = _autenticar(db, request, dados.username, dados.password)
    return TokenOut(access_token=criar_token(u), usuario=UsuarioResumo.model_validate(u))


@router.post("/login-json", response_model=TokenOut)
def login_json(dados: LoginIn, request: Request, db: Session = Depends(get_db)):
    u = _autenticar(db, request, dados.email, dados.senha)
    return TokenOut(access_token=criar_token(u), usuario=UsuarioResumo.model_validate(u))


@router.get("/me", response_model=UsuarioResumo)
def me(usuario: Usuario = Depends(usuario_atual)):
    return usuario
