from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Alergia, Cidadao, MedicamentoEmUso, Usuario
from ...schemas import (
    AlergiaIn,
    AlergiaOut,
    CidadaoCreate,
    CidadaoOut,
    CidadaoUpdate,
    MedicamentoUsoIn,
    MedicamentoUsoOut,
)
from ...security import exigir_perfis, usuario_atual
from ...util import cidadao_dict

router = APIRouter(prefix="/api/cidadaos", tags=["cidadaos"])
_CADASTRO = exigir_perfis("RECEPCAO", "ENFERMEIRO")
_CLINICO = exigir_perfis("MEDICO", "ENFERMEIRO")


def _get(db: Session, cid: str) -> Cidadao:
    c = db.get(Cidadao, cid)
    if not c:
        raise HTTPException(404, "Cidadão não encontrado")
    return c


@router.get("", response_model=list[CidadaoOut])
def listar(q: str | None = Query(default=None), _: Usuario = Depends(usuario_atual),
           db: Session = Depends(get_db)):
    stmt = select(Cidadao).order_by(Cidadao.nome_completo).limit(100)
    if q:
        t = f"%{q}%"
        stmt = stmt.where(or_(Cidadao.nome_completo.ilike(t), Cidadao.cpf.ilike(t),
                              Cidadao.cns.ilike(t)))
    return [cidadao_dict(c) for c in db.scalars(stmt)]


@router.post("", response_model=CidadaoOut, status_code=201)
def criar(dados: CidadaoCreate, _: Usuario = Depends(_CADASTRO), db: Session = Depends(get_db)):
    if dados.cpf and db.scalar(select(Cidadao).where(Cidadao.cpf == dados.cpf)):
        raise HTTPException(409, "Já existe cidadão com este CPF")
    c = Cidadao(**dados.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return cidadao_dict(c)


@router.get("/{cid}", response_model=CidadaoOut)
def obter(cid: str, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return cidadao_dict(_get(db, cid))


@router.put("/{cid}", response_model=CidadaoOut)
def atualizar(cid: str, dados: CidadaoUpdate, _: Usuario = Depends(_CADASTRO),
              db: Session = Depends(get_db)):
    c = _get(db, cid)
    for k, v in dados.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return cidadao_dict(c)


# ---------- Alergias ----------
@router.get("/{cid}/alergias", response_model=list[AlergiaOut])
def listar_alergias(cid: str, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    _get(db, cid)
    return db.scalars(
        select(Alergia).where(Alergia.cidadao_id == cid).order_by(Alergia.registrado_em.desc())
    ).all()


@router.post("/{cid}/alergias", response_model=AlergiaOut, status_code=201)
def add_alergia(cid: str, dados: AlergiaIn, _: Usuario = Depends(_CLINICO),
                db: Session = Depends(get_db)):
    _get(db, cid)
    a = Alergia(cidadao_id=cid, **dados.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{cid}/alergias/{aid}", status_code=204)
def remover_alergia(cid: str, aid: str, _: Usuario = Depends(_CLINICO),
                    db: Session = Depends(get_db)):
    a = db.get(Alergia, aid)
    if not a or str(a.cidadao_id) != cid:
        raise HTTPException(404, "Alergia não encontrada")
    db.delete(a)
    db.commit()


# ---------- Medicamentos em uso ----------
@router.get("/{cid}/medicamentos", response_model=list[MedicamentoUsoOut])
def listar_medicamentos(cid: str, ativos: bool = True, _: Usuario = Depends(usuario_atual),
                        db: Session = Depends(get_db)):
    _get(db, cid)
    stmt = select(MedicamentoEmUso).where(MedicamentoEmUso.cidadao_id == cid)
    if ativos:
        stmt = stmt.where(MedicamentoEmUso.ativo == True)  # noqa: E712
    return db.scalars(stmt).all()


@router.post("/{cid}/medicamentos", response_model=MedicamentoUsoOut, status_code=201)
def add_medicamento(cid: str, dados: MedicamentoUsoIn, _: Usuario = Depends(_CLINICO),
                    db: Session = Depends(get_db)):
    _get(db, cid)
    m = MedicamentoEmUso(cidadao_id=cid, **dados.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{cid}/medicamentos/{mid}", status_code=204)
def remover_medicamento(cid: str, mid: str, _: Usuario = Depends(_CLINICO),
                        db: Session = Depends(get_db)):
    m = db.get(MedicamentoEmUso, mid)
    if not m or str(m.cidadao_id) != cid:
        raise HTTPException(404, "Medicamento não encontrado")
    m.ativo = False
    db.commit()
