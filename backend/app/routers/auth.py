from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Usuario
from ..schemas import LoginIn, TokenOut, UsuarioResumo
from ..security import criar_token, usuario_atual, verificar_senha

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _autenticar(db: Session, email: str, senha: str) -> Usuario:
    u = db.scalar(select(Usuario).where(Usuario.email == email.lower().strip()))
    if not u or not verificar_senha(senha, u.senha_hash):
        raise HTTPException(401, "E-mail ou senha incorretos")
    if not u.ativo:
        raise HTTPException(403, "Usuário inativo")
    return u


@router.post("/login", response_model=TokenOut)
def login(dados: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = _autenticar(db, dados.username, dados.password)
    return TokenOut(access_token=criar_token(u), usuario=UsuarioResumo.model_validate(u))


@router.post("/login-json", response_model=TokenOut)
def login_json(dados: LoginIn, db: Session = Depends(get_db)):
    u = _autenticar(db, dados.email, dados.senha)
    return TokenOut(access_token=criar_token(u), usuario=UsuarioResumo.model_validate(u))


@router.get("/me", response_model=UsuarioResumo)
def me(usuario: Usuario = Depends(usuario_atual)):
    return usuario
