"""Diagnóstico digitado à mão (sem CID-10/CIAP-2) e catálogos em ordem alfabética."""
from tests.conftest import auth_headers


def test_problema_livre_sem_codigo(client):
    # João já entra na fila pelo seed de demonstração — evita 409 "já na fila"
    h_med = auth_headers(client, "medico@ubs.local")
    fila = client.get("/api/fila", headers=h_med).json()
    item = next(i for i in fila if i["cidadao"]["nome_completo"] == "João Batista Ferreira")
    client.post(f"/api/fila/{item['id']}/atender", headers=h_med)

    r = client.post(f"/api/atendimentos/{item['id']}/problemas",
                    json={"sistema": "LIVRE", "codigo": None, "descricao": "Quadro atípico sem código formal"},
                    headers=h_med)
    assert r.status_code == 201, r.text
    assert r.json()["codigo"] is None
    assert r.json()["sistema"] == "LIVRE"


def test_cid10_ordenado_alfabeticamente(client):
    h = auth_headers(client, "medico@ubs.local")
    r = client.get("/api/catalogo/cid10", headers=h)
    assert r.status_code == 200
    descricoes = [item["descricao"] for item in r.json()]
    assert descricoes == sorted(descricoes)
