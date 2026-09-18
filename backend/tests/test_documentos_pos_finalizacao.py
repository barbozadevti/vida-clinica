"""Atestado retroativo (após o atendimento já finalizado) e separação entre
receita simples e receita de controle especial."""
from tests.conftest import auth_headers


def _finalizar_atendimento_joao(client):
    h_med = auth_headers(client, "medico@ubs.local")
    fila = client.get("/api/fila", headers=h_med).json()
    item = next(i for i in fila if i["cidadao"]["nome_completo"] == "João Batista Ferreira")
    client.post(f"/api/fila/{item['id']}/atender", headers=h_med)
    client.put(f"/api/atendimentos/{item['id']}/soap", json={"avaliacao": "Avaliação de rotina."}, headers=h_med)
    r = client.post(f"/api/atendimentos/{item['id']}/finalizar", json={"desfecho": "ALTA"}, headers=h_med)
    assert r.status_code == 200, r.text
    return item["id"], h_med


def test_emitir_atestado_depois_de_finalizado(client):
    aid, h = _finalizar_atendimento_joao(client)
    # confirma que o registro clínico em si continua travado
    r_soap = client.put(f"/api/atendimentos/{aid}/soap", json={"avaliacao": "tentando editar"}, headers=h)
    assert r_soap.status_code == 409

    # mas emitir um atestado que o paciente pediu depois tem que funcionar
    r = client.post(f"/api/atendimentos/{aid}/atestados",
                    json={"tipo": "COMPARECIMENTO"}, headers=h)
    assert r.status_code == 201, r.text
    assert "João" in r.json()["texto"] or "atendimento médico" in r.json()["texto"]


def test_atestado_pos_finalizacao_nao_exige_ser_o_mesmo_profissional(client):
    aid, _ = _finalizar_atendimento_joao(client)
    # outro clínico (não quem atendeu) também pode emitir o atestado avulso
    h_outro = auth_headers(client, "enfermagem@ubs.local")
    r = client.post(f"/api/atendimentos/{aid}/atestados", json={"tipo": "COMPARECIMENTO"}, headers=h_outro)
    assert r.status_code == 201, r.text


def test_receita_simples_e_controle_especial_ficam_separadas(client):
    h_med = auth_headers(client, "medico@ubs.local")
    fila = client.get("/api/fila", headers=h_med).json()
    item = next(i for i in fila if i["cidadao"]["nome_completo"] == "João Batista Ferreira")
    client.post(f"/api/fila/{item['id']}/atender", headers=h_med)

    r1 = client.post(f"/api/atendimentos/{item['id']}/prescricoes", json={
        "medicamento": "Paracetamol 500 mg", "posologia": "1 comp de 6/6h se dor", "controle_especial": False,
    }, headers=h_med)
    r2 = client.post(f"/api/atendimentos/{item['id']}/prescricoes", json={
        "medicamento": "Diazepam 10 mg", "posologia": "1 comp à noite", "controle_especial": True,
    }, headers=h_med)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["controle_especial"] is False
    assert r2.json()["controle_especial"] is True

    doc_simples = client.get(f"/api/atendimentos/{item['id']}/documento/receita-simples", headers=h_med)
    assert doc_simples.status_code == 200
    assert "Paracetamol" in doc_simples.json()["html"]
    assert "Diazepam" not in doc_simples.json()["html"]

    doc_controle = client.get(f"/api/atendimentos/{item['id']}/documento/receita-controle", headers=h_med)
    assert doc_controle.status_code == 200
    assert "Diazepam" in doc_controle.json()["html"]
    assert "Paracetamol" not in doc_controle.json()["html"]
    assert "CONTROLE ESPECIAL" in doc_controle.json()["html"]
