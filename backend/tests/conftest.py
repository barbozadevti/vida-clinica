"""Config compartilhada dos testes: banco isolado (esus_test), zerado e
re-semeado a cada teste com o mesmo bootstrap que roda em produção."""
import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/esus_test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models  # noqa: F401 -- registra todas as tabelas em Base.metadata
from app.database import Base, engine

Base.metadata.create_all(bind=engine)
_TABELAS = ", ".join(t.name for t in Base.metadata.sorted_tables)


@pytest.fixture(autouse=True)
def _banco_limpo():
    """Zera tudo antes de cada teste; o startup do app (via TestClient)
    re-semeia os dados de demonstração, então cada teste começa do mesmo
    estado conhecido (Dr. Victor Dalvi na Centro, Dra. Camila Duarte na
    Sul, pacientes, fila etc. — ver app/bootstrap.py)."""
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {_TABELAS} RESTART IDENTITY CASCADE"))
    from app import ratelimit
    ratelimit._falhas.clear()  # limitador de login é estado em memória do processo
    yield


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def login(client, email: str, senha: str = "123456") -> dict:
    r = client.post("/api/auth/login-json", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    return r.json()


def auth_headers(client, email: str, senha: str = "123456") -> dict:
    token = login(client, email, senha)["access_token"]
    return {"Authorization": f"Bearer {token}"}
