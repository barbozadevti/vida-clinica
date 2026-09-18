"""Encaminhamento para especialista — regressão do bug relatado nesta sessão:
o autocomplete de CID manda "código — descrição" (não só o código) pro campo,
e a coluna era curta demais (VARCHAR(10)) pra isso, derrubando a finalização
do atendimento com "campo excede o tamanho máximo"."""
from tests.conftest import auth_headers


def _paciente_em_atendimento(client):
    # João já entra na fila pelo próprio seed de demonstração (bootstrap.py)
    # — usa esse item existente em vez de criar outro (senão dá 409, "já
    # está na fila").
    h_med = auth_headers(client, "medico@ubs.local")
    fila = client.get("/api/fila", headers=h_med).json()
    item = next(i for i in fila if i["cidadao"]["nome_completo"] == "João Batista Ferreira")
    client.post(f"/api/fila/{item['id']}/atender", headers=h_med)
    return item["id"], h_med


def test_encaminhamento_com_cid_codigo_e_descricao_longos_nao_quebra(client):
    aid, h = _paciente_em_atendimento(client)
    client.put(f"/api/atendimentos/{aid}/soap", json={"avaliacao": "Hipertrofia das amígdalas (J35.1)."}, headers=h)

    r = client.post(f"/api/atendimentos/{aid}/finalizar", json={
        "desfecho": "ENCAMINHAMENTO",
        "encaminhamento_tipo": "AVALIACAO_CIRURGICA",
        "encaminhamento_especialidade": "OTORRINO",
        # exatamente o valor que o autocomplete do CID manda: código + descrição,
        # não só o código -- isso é o que estourava a coluna antes do fix.
        "encaminhamento_cid": "J35.1 — Hipertrofia das amígdalas",
        "encaminhamento_motivo": "CIRURGIA",
        "encaminhamento_prioridade": "PRIORITARIO",
        "desfecho_obs": "DNLKSAFLAKSFKSAFKL",
    }, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "FINALIZADO"


def test_encaminhamento_sem_especialidade_ou_motivo_da_400(client):
    aid, h = _paciente_em_atendimento(client)
    client.put(f"/api/atendimentos/{aid}/soap", json={"avaliacao": "Avaliação qualquer."}, headers=h)
    r = client.post(f"/api/atendimentos/{aid}/finalizar", json={"desfecho": "ENCAMINHAMENTO"}, headers=h)
    assert r.status_code == 400
