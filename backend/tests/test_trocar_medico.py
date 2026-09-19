"""'Trocar de médico': direcionar um atendimento da fila para um profissional
específico (ex.: paciente pede a Dra. Katia em vez do Dr. Victor)."""
from tests.conftest import auth_headers


def _novo_paciente_na_fila(client, h_recep, profissional_id=None):
    r = client.post("/api/cidadaos", json={
        "nome_completo": "Paciente Teste Trocar Medico", "cpf": "12345678909",
        "data_nascimento": "1990-01-01", "sexo": "F",
    }, headers=h_recep)
    assert r.status_code == 201, r.text
    cidadao_id = r.json()["id"]
    body = {"cidadao_id": cidadao_id, "motivo": "Consulta de rotina"}
    if profissional_id:
        body["profissional_id"] = profissional_id
    r = client.post("/api/fila", json=body, headers=h_recep)
    assert r.status_code == 201, r.text
    return r.json()


def _id_katia(client, h_recep):
    profs = client.get("/api/usuarios", headers=h_recep).json()
    return next(u["id"] for u in profs if u["email"] == "katia@ubs.local")


def test_direcionar_para_profissional_ao_adicionar_na_fila(client):
    h_recep = auth_headers(client, "recepcao@ubs.local")
    katia_id = _id_katia(client, h_recep)
    item = _novo_paciente_na_fila(client, h_recep, profissional_id=katia_id)
    assert "Katia" in item["profissional"]["nome"]


def test_outro_medico_nao_pode_atender_atendimento_direcionado(client):
    h_recep = auth_headers(client, "recepcao@ubs.local")
    katia_id = _id_katia(client, h_recep)
    item = _novo_paciente_na_fila(client, h_recep, profissional_id=katia_id)

    h_victor = auth_headers(client, "medico@ubs.local")
    r = client.post(f"/api/fila/{item['id']}/atender", headers=h_victor)
    assert r.status_code == 409
    assert "Katia" in r.json()["detail"]

    h_katia = auth_headers(client, "katia@ubs.local")
    r = client.post(f"/api/fila/{item['id']}/atender", headers=h_katia)
    assert r.status_code == 200, r.text


def test_admin_pode_atender_mesmo_atendimento_direcionado(client):
    h_recep = auth_headers(client, "recepcao@ubs.local")
    katia_id = _id_katia(client, h_recep)
    item = _novo_paciente_na_fila(client, h_recep, profissional_id=katia_id)

    h_admin = auth_headers(client, "admin@ubs.local")
    r = client.post(f"/api/fila/{item['id']}/atender", headers=h_admin)
    assert r.status_code == 200, r.text


def test_trocar_profissional_endpoint_define_muda_e_limpa_preferencia(client):
    h_recep = auth_headers(client, "recepcao@ubs.local")
    katia_id = _id_katia(client, h_recep)
    item = _novo_paciente_na_fila(client, h_recep)
    assert item["profissional"] is None

    r = client.post(f"/api/fila/{item['id']}/profissional", json={"profissional_id": katia_id}, headers=h_recep)
    assert r.status_code == 200, r.text
    assert "Katia" in r.json()["profissional"]["nome"]

    r = client.post(f"/api/fila/{item['id']}/profissional", json={"profissional_id": None}, headers=h_recep)
    assert r.status_code == 200, r.text
    assert r.json()["profissional"] is None


def test_nao_pode_trocar_profissional_apos_atendimento_iniciado(client):
    h_recep = auth_headers(client, "recepcao@ubs.local")
    katia_id = _id_katia(client, h_recep)
    item = _novo_paciente_na_fila(client, h_recep)

    h_katia = auth_headers(client, "katia@ubs.local")
    client.post(f"/api/fila/{item['id']}/atender", headers=h_katia)

    r = client.post(f"/api/fila/{item['id']}/profissional", json={"profissional_id": katia_id}, headers=h_recep)
    assert r.status_code == 409
