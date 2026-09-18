"""Filtro por unidade — fila, agenda, relatório e painel. Regressão da Onda 5
(Lean Inception): cada usuário só vê a própria unidade; ADMIN vê tudo."""
from tests.conftest import auth_headers


def test_fila_medico_centro_so_ve_pacientes_da_centro(client):
    h = auth_headers(client, "medico@ubs.local")
    r = client.get("/api/fila", headers=h)
    assert r.status_code == 200
    nomes = {i["cidadao"]["nome_completo"] for i in r.json()}
    assert "João Batista Ferreira" in nomes
    assert "Marcelo Tavares Costa" not in nomes  # esse é da Unidade Sul


def test_fila_medico_sul_so_ve_pacientes_da_sul(client):
    h = auth_headers(client, "medico.sul@ubs.local")
    r = client.get("/api/fila", headers=h)
    assert r.status_code == 200
    nomes = {i["cidadao"]["nome_completo"] for i in r.json()}
    assert "Marcelo Tavares Costa" in nomes
    assert "João Batista Ferreira" not in nomes  # esse é da Unidade Centro


def test_fila_admin_ve_as_duas_unidades(client):
    h = auth_headers(client, "admin@ubs.local")
    r = client.get("/api/fila", headers=h)
    assert r.status_code == 200
    nomes = {i["cidadao"]["nome_completo"] for i in r.json()}
    assert "João Batista Ferreira" in nomes
    assert "Marcelo Tavares Costa" in nomes


def test_relatorio_producao_filtrado_por_unidade_para_admin(client):
    h = auth_headers(client, "admin@ubs.local")

    r_geral = client.get("/api/relatorios/producao", headers=h)
    assert r_geral.status_code == 200
    total_geral = r_geral.json()["total"]

    # pega o id da Unidade Sul via cadastro de unidades
    unidades = client.get("/api/unidades", headers=h).json()
    sul = next(u for u in unidades if "Sul" in u["nome"])

    r_sul = client.get(f"/api/relatorios/producao?unidade_id={sul['id']}", headers=h)
    assert r_sul.status_code == 200
    assert r_sul.json()["total"] <= total_geral


def test_novo_atendimento_da_fila_herda_a_unidade_do_usuario(client):
    h = auth_headers(client, "recepcao.sul@ubs.local")
    cidadaos = client.get("/api/cidadaos?q=Isabela", headers=h).json()
    isabela = cidadaos[0]

    # cancela o atendimento sazonal que o seed já colocou na fila, se existir,
    # pra poder adicionar de novo sem esbarrar na trava de "já está na fila"
    fila = client.get("/api/fila", headers=h).json()
    for item in fila:
        if item["cidadao"]["id"] == isabela["id"]:
            client.post(f"/api/fila/{item['id']}/cancelar", headers=h)

    r = client.post("/api/fila", json={"cidadao_id": isabela["id"], "tipo": "CONSULTA",
                                       "motivo": "Teste automatizado"}, headers=h)
    assert r.status_code == 201

    # quem está na Centro não deve enxergar esse novo atendimento
    h_centro = auth_headers(client, "medico@ubs.local")
    fila_centro = client.get("/api/fila", headers=h_centro).json()
    assert isabela["id"] not in {i["cidadao"]["id"] for i in fila_centro}
