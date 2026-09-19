"""Chegada do paciente agendado (Agenda -> 'Paciente chegou' -> fila) precisa
levar o profissional escolhido no agendamento para o atendimento criado —
senão qualquer médico pode 'roubar' uma consulta marcada com outro (ex.:
agendado com a Dra. Katia, mas o Dr. Victor consegue atender)."""
from datetime import date, timedelta

from tests.conftest import auth_headers


def _id_katia(client, h):
    profs = client.get("/api/usuarios", headers=h).json()
    return next(u["id"] for u in profs if u["email"] == "katia@ubs.local")


def _agendar_com_katia(client, h_recep, katia_id):
    r = client.post("/api/cidadaos", json={
        "nome_completo": "Paciente Teste Agenda Fila", "cpf": "12312312312",
        "data_nascimento": "1990-01-01", "sexo": "F",
    }, headers=h_recep)
    assert r.status_code == 201, r.text
    cidadao_id = r.json()["id"]
    data_futura = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/api/agenda", json={
        "cidadao_id": cidadao_id, "profissional_id": katia_id,
        "data": data_futura, "hora": "09:00", "tipo": "CONSULTA",
    }, headers=h_recep)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_chegada_leva_o_profissional_agendado_para_o_atendimento(client):
    h_recep = auth_headers(client, "recepcao@ubs.local")
    katia_id = _id_katia(client, h_recep)
    ag_id = _agendar_com_katia(client, h_recep, katia_id)

    r = client.post(f"/api/agenda/{ag_id}/enviar-fila", headers=h_recep)
    assert r.status_code == 200, r.text
    assert r.json()["profissional"]["id"] == katia_id


def test_outro_medico_nao_pode_atender_consulta_agendada_com_outro(client):
    h_recep = auth_headers(client, "recepcao@ubs.local")
    katia_id = _id_katia(client, h_recep)
    ag_id = _agendar_com_katia(client, h_recep, katia_id)
    at = client.post(f"/api/agenda/{ag_id}/enviar-fila", headers=h_recep).json()

    h_victor = auth_headers(client, "medico@ubs.local")
    r = client.post(f"/api/fila/{at['id']}/atender", headers=h_victor)
    assert r.status_code == 409
    assert "Katia" in r.json()["detail"]

    h_katia = auth_headers(client, "katia@ubs.local")
    r = client.post(f"/api/fila/{at['id']}/atender", headers=h_katia)
    assert r.status_code == 200, r.text
