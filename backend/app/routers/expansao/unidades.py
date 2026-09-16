"""Onda 5 (Lean Inception) — multiclínica: cadastro de unidades/filiais."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Unidade, Usuario
from ...schemas import UnidadeIn, UnidadeOut
from ...security import exigir_perfis, usuario_atual

router = APIRouter(prefix="/api/unidades", tags=["unidades (multiclínica)"])
_ADMIN = exigir_perfis("ADMIN")


@router.get("", response_model=list[UnidadeOut])
def listar(_: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return db.scalars(select(Unidade).order_by(Unidade.nome)).all()


@router.post("", response_model=UnidadeOut, status_code=201)
def criar(dados: UnidadeIn, _: Usuario = Depends(_ADMIN), db: Session = Depends(get_db)):
    if db.scalar(select(Unidade).where(Unidade.nome == dados.nome)):
        raise HTTPException(409, "Já existe uma unidade com esse nome")
    u = Unidade(**dados.model_dump())
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.put("/{uid}", response_model=UnidadeOut)
def atualizar(uid: str, dados: UnidadeIn, _: Usuario = Depends(_ADMIN), db: Session = Depends(get_db)):
    u = db.get(Unidade, uid)
    if not u:
        raise HTTPException(404, "Unidade não encontrada")
    for k, v in dados.model_dump().items():
        setattr(u, k, v)
    db.commit()
    db.refresh(u)
    return u
