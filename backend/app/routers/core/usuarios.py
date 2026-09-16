from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Usuario
from ...schemas import UsuarioCreate, UsuarioOut, UsuarioUpdate
from ...security import PERFIS, exigir_perfis, hash_senha, usuario_atual

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])
_ADMIN = exigir_perfis("ADMIN")


@router.get("", response_model=list[UsuarioOut])
def listar(perfil: str | None = None, _: Usuario = Depends(usuario_atual),
           db: Session = Depends(get_db)):
    stmt = select(Usuario).order_by(Usuario.nome)
    if perfil:
        stmt = stmt.where(Usuario.perfil == perfil.upper())
    return db.scalars(stmt).all()


@router.post("", response_model=UsuarioOut, status_code=201)
def criar(dados: UsuarioCreate, _: Usuario = Depends(_ADMIN), db: Session = Depends(get_db)):
    if dados.perfil.upper() not in PERFIS:
        raise HTTPException(400, f"Perfil inválido: {sorted(PERFIS)}")
    if db.scalar(select(Usuario).where(Usuario.email == dados.email.lower())):
        raise HTTPException(409, "E-mail já cadastrado")
    payload = dados.model_dump(exclude={"senha"})
    payload["email"] = dados.email.lower().strip()
    payload["perfil"] = dados.perfil.upper()
    u = Usuario(**payload, senha_hash=hash_senha(dados.senha))
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.put("/{uid}", response_model=UsuarioOut)
def atualizar(uid: str, dados: UsuarioUpdate, _: Usuario = Depends(_ADMIN),
              db: Session = Depends(get_db)):
    u = db.get(Usuario, uid)
    if not u:
        raise HTTPException(404, "Usuário não encontrado")
    payload = dados.model_dump(exclude_unset=True)
    if payload.get("senha"):
        u.senha_hash = hash_senha(payload.pop("senha"))
    else:
        payload.pop("senha", None)
    if payload.get("email"):
        payload["email"] = payload["email"].lower().strip()
    if payload.get("perfil"):
        payload["perfil"] = payload["perfil"].upper()
        if payload["perfil"] not in PERFIS:
            raise HTTPException(400, "Perfil inválido")
    for k, v in payload.items():
        setattr(u, k, v)
    db.commit()
    db.refresh(u)
    return u
