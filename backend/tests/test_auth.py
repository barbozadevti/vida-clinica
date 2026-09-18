"""Login e permissões básicas de cada perfil."""


def test_login_ok(client):
    r = client.post("/api/auth/login-json", json={"email": "medico@ubs.local", "senha": "123456"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["usuario"]["nome"] == "Dr. Victor Dalvi"
    assert corpo["usuario"]["perfil"] == "MEDICO"
    assert corpo["access_token"]


def test_login_senha_errada(client):
    r = client.post("/api/auth/login-json", json={"email": "medico@ubs.local", "senha": "errada"})
    assert r.status_code == 401


def test_login_email_inexistente(client):
    r = client.post("/api/auth/login-json", json={"email": "ninguem@ubs.local", "senha": "123456"})
    assert r.status_code == 401


def test_endpoint_exige_autenticacao(client):
    r = client.get("/api/cidadaos")
    assert r.status_code in (401, 403)


def test_recepcao_nao_acessa_endpoint_so_de_medico_enfermeiro(client):
    from tests.conftest import auth_headers

    r = client.get("/api/relatorios/producao", headers=auth_headers(client, "recepcao@ubs.local"))
    assert r.status_code == 403
