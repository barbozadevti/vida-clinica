"""Proteção contra força bruta no login (equipe e portal do paciente)."""


def test_login_bloqueia_apos_muitas_tentativas_erradas(client):
    for _ in range(5):
        r = client.post("/api/auth/login-json", json={"email": "medico@ubs.local", "senha": "errada"})
        assert r.status_code == 401
    r = client.post("/api/auth/login-json", json={"email": "medico@ubs.local", "senha": "errada"})
    assert r.status_code == 429
    # nem com a senha certa passa enquanto o bloqueio estiver de pé
    r = client.post("/api/auth/login-json", json={"email": "medico@ubs.local", "senha": "123456"})
    assert r.status_code == 429


def test_login_correto_nao_conta_como_falha(client):
    for _ in range(4):
        client.post("/api/auth/login-json", json={"email": "medico@ubs.local", "senha": "errada"})
    r = client.post("/api/auth/login-json", json={"email": "medico@ubs.local", "senha": "123456"})
    assert r.status_code == 200  # login certo limpa o contador
    r = client.post("/api/auth/login-json", json={"email": "medico@ubs.local", "senha": "errada"})
    assert r.status_code == 401  # ainda não bloqueado, contador tinha zerado


def test_portal_bloqueia_apos_muitas_tentativas_erradas(client):
    for _ in range(5):
        r = client.post("/api/portal/entrar", json={"cpf": "11122233344", "data_nascimento": "1900-01-01"})
        assert r.status_code == 401
    r = client.post("/api/portal/entrar", json={"cpf": "11122233344", "data_nascimento": "1966-03-14"})
    assert r.status_code == 429
