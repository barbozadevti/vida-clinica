"""Log de auditoria (LGPD) — rastreabilidade de quem acessou/alterou o quê
no prontuário. Só o ADMIN consulta o log."""
from tests.conftest import auth_headers


def test_login_gera_log(client):
    auth_headers(client, "medico@ubs.local")
    h_admin = auth_headers(client, "admin@ubs.local")
    r = client.get("/api/auditoria?acao=LOGIN", headers=h_admin)
    assert r.status_code == 200, r.text
    acoes = [l["acao"] for l in r.json()]
    assert "LOGIN" in acoes


def test_visualizar_paciente_gera_log(client):
    h_med = auth_headers(client, "medico@ubs.local")
    cids = client.get("/api/cidadaos", headers=h_med).json()
    joao = next(c for c in cids if c["nome_completo"] == "João Batista Ferreira")
    client.get(f"/api/cidadaos/{joao['id']}", headers=h_med)

    h_admin = auth_headers(client, "admin@ubs.local")
    r = client.get(f"/api/auditoria?acao=VISUALIZOU_PACIENTE&cidadao_id={joao['id']}", headers=h_admin)
    assert r.status_code == 200, r.text
    assert len(r.json()) >= 1
    assert r.json()[0]["usuario"]["nome"] == "Dr. Victor Dalvi"


def test_finalizar_atendimento_gera_log(client):
    h_med = auth_headers(client, "medico@ubs.local")
    fila = client.get("/api/fila", headers=h_med).json()
    item = next(i for i in fila if i["cidadao"]["nome_completo"] == "João Batista Ferreira")
    client.post(f"/api/fila/{item['id']}/atender", headers=h_med)
    client.put(f"/api/atendimentos/{item['id']}/soap", json={"avaliacao": "Avaliação de rotina."}, headers=h_med)
    r = client.post(f"/api/atendimentos/{item['id']}/finalizar", json={"desfecho": "ALTA"}, headers=h_med)
    assert r.status_code == 200, r.text

    h_admin = auth_headers(client, "admin@ubs.local")
    r = client.get(f"/api/auditoria?atendimento_id={item['id']}", headers=h_admin)
    assert r.status_code == 200, r.text
    acoes = [l["acao"] for l in r.json()]
    assert "EDITOU_SOAP" in acoes
    assert "FINALIZOU_ATENDIMENTO" in acoes


def test_medico_nao_pode_consultar_auditoria(client):
    h_med = auth_headers(client, "medico@ubs.local")
    r = client.get("/api/auditoria", headers=h_med)
    assert r.status_code == 403
