"""Nota fiscal de serviço substitui o recibo — por lei, todo procedimento
ou consulta precisa de nota fiscal, seja pessoa física ou jurídica. Emitir
(POST) é uma ação do setor financeiro/recepção, separada de imprimir (GET)."""
from tests.conftest import auth_headers


def _joao_id(client, h):
    cids = client.get("/api/cidadaos", headers=h).json()
    return next(c["id"] for c in cids if c["nome_completo"] == "João Batista Ferreira")


def _cobranca_paga_pf(client, h):
    joao_id = _joao_id(client, h)
    r = client.post("/api/financeiro/cobrancas", json={
        "cidadao_id": joao_id, "descricao": "Consulta particular", "valor": 250.0,
        "forma_pagamento": "DINHEIRO",
    }, headers=h)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    r = client.post(f"/api/financeiro/cobrancas/{cid}/pagar", headers=h)
    assert r.status_code == 200, r.text
    return cid


def test_imprimir_sem_emitir_primeiro_da_409(client):
    h = auth_headers(client, "recepcao@ubs.local")
    cid = _cobranca_paga_pf(client, h)

    r = client.get(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h)
    assert r.status_code == 409


def test_emitir_nota_fiscal_pessoa_fisica(client):
    h = auth_headers(client, "recepcao@ubs.local")
    cid = _cobranca_paga_pf(client, h)

    r = client.post(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["numero_nf"]

    r = client.get(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h)
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert "Pessoa Física" in html
    assert "João" in html
    assert "111.222.333-44" in html  # CPF formatado de João Batista Ferreira


def test_reemissao_reusa_o_mesmo_numero(client):
    h = auth_headers(client, "recepcao@ubs.local")
    cid = _cobranca_paga_pf(client, h)

    n1 = client.post(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h).json()["numero_nf"]
    n2 = client.post(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h).json()["numero_nf"]
    assert n1 == n2


def test_numeracao_sequencial_entre_cobrancas_diferentes(client):
    h = auth_headers(client, "recepcao@ubs.local")
    cid1 = _cobranca_paga_pf(client, h)
    cid2 = _cobranca_paga_pf(client, h)

    n1 = client.post(f"/api/financeiro/cobrancas/{cid1}/nota-fiscal", headers=h).json()["numero_nf"]
    n2 = client.post(f"/api/financeiro/cobrancas/{cid2}/nota-fiscal", headers=h).json()["numero_nf"]
    assert n1 != n2


def test_emitir_nota_fiscal_pessoa_juridica_via_convenio(client):
    h = auth_headers(client, "recepcao@ubs.local")
    joao_id = _joao_id(client, h)
    convs = client.get("/api/convenios", headers=h).json()
    unimed = next(c for c in convs if c["nome"] == "Unimed Regional")
    assert unimed["cnpj"]  # convênio já vem com CNPJ cadastrado (pessoa jurídica)

    r = client.post("/api/financeiro/cobrancas", json={
        "cidadao_id": joao_id, "descricao": "Consulta via convênio", "valor": 180.0,
        "forma_pagamento": "CONVENIO", "convenio_id": unimed["id"],
    }, headers=h)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    client.post(f"/api/financeiro/cobrancas/{cid}/pagar", headers=h)
    client.post(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h)

    r = client.get(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h)
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert "Pessoa Jurídica" in html
    assert "Unimed Regional" in html


def test_cobranca_cancelada_nao_emite_nota_fiscal(client):
    h = auth_headers(client, "recepcao@ubs.local")
    joao_id = _joao_id(client, h)
    r = client.post("/api/financeiro/cobrancas", json={
        "cidadao_id": joao_id, "descricao": "Consulta cancelada", "valor": 100.0,
        "forma_pagamento": "DINHEIRO",
    }, headers=h)
    cid = r.json()["id"]
    client.post(f"/api/financeiro/cobrancas/{cid}/cancelar", headers=h)

    r = client.post(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h)
    assert r.status_code == 409


def test_medico_nao_pode_emitir_nota_fiscal(client):
    """Emissão de nota fiscal é do setor financeiro/recepção, não do médico."""
    h_recep = auth_headers(client, "recepcao@ubs.local")
    cid = _cobranca_paga_pf(client, h_recep)

    h_medico = auth_headers(client, "medico@ubs.local")
    r = client.post(f"/api/financeiro/cobrancas/{cid}/nota-fiscal", headers=h_medico)
    assert r.status_code == 403
