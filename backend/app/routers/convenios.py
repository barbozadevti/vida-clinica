from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Convenio, Usuario
from ..schemas import ConvenioIn, ConvenioOut
from ..security import exigir_perfis, usuario_atual

router = APIRouter(prefix="/api/convenios", tags=["convênios"])
_GESTAO = exigir_perfis("ADMIN", "RECEPCAO")


@router.get("", response_model=list[ConvenioOut])
def listar(_: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return db.scalars(select(Convenio).order_by(Convenio.nome)).all()


@router.post("", response_model=ConvenioOut, status_code=201)
def criar(dados: ConvenioIn, _: Usuario = Depends(_GESTAO), db: Session = Depends(get_db)):
    if db.scalar(select(Convenio).where(Convenio.nome == dados.nome)):
        raise HTTPException(409, "Convênio já cadastrado")
    c = Convenio(**dados.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/{cid}", response_model=ConvenioOut)
def atualizar(cid: str, dados: ConvenioIn, _: Usuario = Depends(_GESTAO), db: Session = Depends(get_db)):
    c = db.get(Convenio, cid)
    if not c:
        raise HTTPException(404, "Convênio não encontrado")
    for k, v in dados.model_dump().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c
