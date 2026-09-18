"""Cadastro de pacientes — inclui teste de regressão do bug corrigido nesta
sessão: campo maior que o limite da coluna tinha que dar erro 500 cru, e
agora deve dar 422 com mensagem clara."""
from tests.conftest import auth_headers

_PACIENTE_BASE = {
    "nome_completo": "Paciente Teste Automatizado",
    "nome_social": None,
    "cpf": "12345678900",
    "cns": None,
    "data_nascimento": "1990-01-01",
    "sexo": "M",
    "nome_mae": None,
    "telefone": None,
    "endereco": None,
    "convenio_id": None,
    "numero_carteirinha": None,
}


def test_criar_paciente_ok(client):
    h = auth_headers(client, "recepcao@ubs.local")
    r = client.post("/api/cidadaos", json=_PACIENTE_BASE, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["nome_completo"] == "Paciente Teste Automatizado"
    assert "idade" in r.json()


def test_criar_paciente_telefone_maior_que_limite_da_coluna_da_422_nao_500(client):
    # regressão: antes desse fix, um telefone > 20 caracteres derrubava a
    # requisição com um 500 cru (ver commit "Corrige erro 500 ao salvar
    # paciente com campo maior que o limite do banco").
    h = auth_headers(client, "recepcao@ubs.local")
    dados = {**_PACIENTE_BASE, "cpf": "22233344400", "telefone": "Rua Teste Completo, 123 - isso não é telefone"}
    r = client.post("/api/cidadaos", json=dados, headers=h)
    assert r.status_code == 422
    assert "telefone" in r.text


def test_criar_paciente_cpf_duplicado_da_conflito(client):
    h = auth_headers(client, "recepcao@ubs.local")
    r1 = client.post("/api/cidadaos", json=_PACIENTE_BASE, headers=h)
    assert r1.status_code == 201
    r2 = client.post("/api/cidadaos", json=_PACIENTE_BASE, headers=h)
    assert r2.status_code == 409


def test_criar_paciente_sexo_invalido_da_422(client):
    h = auth_headers(client, "recepcao@ubs.local")
    dados = {**_PACIENTE_BASE, "cpf": "33344455500", "sexo": "X"}
    r = client.post("/api/cidadaos", json=dados, headers=h)
    assert r.status_code == 422


def test_medico_nao_cria_paciente_perfil_errado(client):
    # /api/cidadaos POST exige RECEPCAO ou ENFERMEIRO (ou ADMIN)
    h = auth_headers(client, "medico@ubs.local")
    r = client.post("/api/cidadaos", json={**_PACIENTE_BASE, "cpf": "44455566600"}, headers=h)
    assert r.status_code == 403
