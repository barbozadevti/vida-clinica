from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import ItemEstoque, MovimentoEstoque, Usuario
from ...schemas import (
    ItemEstoqueIn,
    ItemEstoqueOut,
    MovimentoEstoqueIn,
    MovimentoEstoqueOut,
)
from ...security import exigir_perfis, usuario_atual

router = APIRouter(prefix="/api/estoque", tags=["estoque"])
_GESTAO = exigir_perfis("ADMIN", "ENFERMEIRO", "RECEPCAO")


@router.get("/itens", response_model=list[ItemEstoqueOut])
def listar(_: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return db.scalars(
        select(ItemEstoque).where(ItemEstoque.ativo == True).order_by(ItemEstoque.nome)  # noqa: E712
    ).all()


@router.post("/itens", response_model=ItemEstoqueOut, status_code=201)
def criar(dados: ItemEstoqueIn, _: Usuario = Depends(_GESTAO), db: Session = Depends(get_db)):
    it = ItemEstoque(**dados.model_dump())
    db.add(it)
    db.commit()
    db.refresh(it)
    return it


@router.put("/itens/{iid}", response_model=ItemEstoqueOut)
def atualizar(iid: str, dados: ItemEstoqueIn, _: Usuario = Depends(_GESTAO), db: Session = Depends(get_db)):
    it = db.get(ItemEstoque, iid)
    if not it:
        raise HTTPException(404, "Item não encontrado")
    for k, v in dados.model_dump().items():
        setattr(it, k, v)
    db.commit()
    db.refresh(it)
    return it


@router.post("/itens/{iid}/movimentar", response_model=ItemEstoqueOut)
def movimentar(iid: str, dados: MovimentoEstoqueIn, usuario: Usuario = Depends(_GESTAO),
               db: Session = Depends(get_db)):
    it = db.get(ItemEstoque, iid)
    if not it:
        raise HTTPException(404, "Item não encontrado")
    if dados.tipo == "ENTRADA":
        it.quantidade += dados.quantidade
    elif dados.tipo == "SAIDA":
        if dados.quantidade > it.quantidade:
            raise HTTPException(400, "Quantidade insuficiente em estoque")
        it.quantidade -= dados.quantidade
    else:  # AJUSTE — define a quantidade absoluta
        it.quantidade = dados.quantidade
    db.add(MovimentoEstoque(item_id=it.id, tipo=dados.tipo, quantidade=dados.quantidade,
                            motivo=dados.motivo, criado_por_id=usuario.id))
    db.commit()
    db.refresh(it)
    return it


@router.get("/itens/{iid}/movimentos", response_model=list[MovimentoEstoqueOut])
def historico(iid: str, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return db.scalars(
        select(MovimentoEstoque).where(MovimentoEstoque.item_id == iid)
        .order_by(MovimentoEstoque.criado_em.desc()).limit(100)
    ).all()
