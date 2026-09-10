"""Cria as tabelas e popula dados iniciais quando o banco está vazio."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, text

from . import catalogos_seed as cat
from .database import Base, SessionLocal, engine
from .models import (
    Alergia,
    Atendimento,
    CatalogoCID,
    CatalogoCIAP,
    CatalogoExame,
    CatalogoMedicamento,
    Cidadao,
    Medicao,
    MedicamentoEmUso,
    Usuario,
)
from .security import hash_senha


def _seed_catalogos(db) -> None:
    if not db.scalar(select(CatalogoCID).limit(1)):
        db.add_all(CatalogoCID(codigo=c, descricao=d) for c, d in cat.CID10)
    if not db.scalar(select(CatalogoCIAP).limit(1)):
        db.add_all(CatalogoCIAP(codigo=c, descricao=d) for c, d in cat.CIAP2)
    if not db.scalar(select(CatalogoMedicamento).limit(1)):
        db.add_all(
            CatalogoMedicamento(nome=n, principio_ativo=p, apresentacao=a)
            for n, p, a in cat.MEDICAMENTOS
        )
    if not db.scalar(select(CatalogoExame).limit(1)):
        db.add_all(CatalogoExame(nome=n, sinonimia=s) for n, s in cat.EXAMES)
    db.commit()


def _seed_demo(db) -> None:
    if db.scalar(select(Usuario).limit(1)):
        return

    admin = Usuario(nome="Administrador", email="admin@ubs.local",
                    senha_hash=hash_senha("123456"), perfil="ADMIN")
    recep = Usuario(nome="Joana Recepção", email="recepcao@ubs.local",
                    senha_hash=hash_senha("123456"), perfil="RECEPCAO", cbo="422105")
    enf = Usuario(nome="Enf. Paulo Lima", email="enfermagem@ubs.local",
                  senha_hash=hash_senha("123456"), perfil="ENFERMEIRO",
                  conselho="COREN 123456-ES", cbo="223505")
    med = Usuario(nome="Dra. Marina Alves", email="medico@ubs.local",
                  senha_hash=hash_senha("123456"), perfil="MEDICO",
                  conselho="CRM 54321-ES", cbo="225125", cns="700000000000001")
    db.add_all([admin, recep, enf, med])
    db.flush()

    agora = datetime.now(timezone.utc)

    # Cidadão 1: hipertenso + diabético, com alergia e histórico de PA/peso
    joao = Cidadao(
        nome_completo="João Batista Ferreira", cpf="11122233344",
        cns="700100200300400", data_nascimento=date(1966, 3, 14), sexo="M",
        nome_mae="Maria Ferreira", telefone="(27) 99999-1010",
        endereco="Rua das Palmeiras, 45 - Centro",
    )
    db.add(joao)
    db.flush()
    db.add(Alergia(cidadao_id=joao.id, substancia="Dipirona",
                   categoria="MEDICAMENTO", gravidade="GRAVE",
                   reacao="Edema de glote em 2019"))
    db.add(Alergia(cidadao_id=joao.id, substancia="AAS / Ácido acetilsalicílico",
                   categoria="MEDICAMENTO", gravidade="MODERADA", reacao="Urticária"))
    db.add_all([
        MedicamentoEmUso(cidadao_id=joao.id, descricao="Losartana 50 mg",
                         posologia="1 comprimido de manhã", via="oral", uso_continuo=True),
        MedicamentoEmUso(cidadao_id=joao.id, descricao="Hidroclorotiazida 25 mg",
                         posologia="1 comprimido de manhã", via="oral", uso_continuo=True),
        MedicamentoEmUso(cidadao_id=joao.id, descricao="Metformina 850 mg",
                         posologia="1 comprimido no almoço e no jantar", via="oral",
                         uso_continuo=True),
    ])
    for i, (pas, pad, peso) in enumerate(
        [(158, 96, 82.0), (150, 92, 81.2), (144, 88, 80.5), (138, 86, 79.8), (136, 84, 79.0)]
    ):
        quando = agora - timedelta(days=(4 - i) * 90)
        db.add_all([
            Medicao(cidadao_id=joao.id, tipo="PA_SISTOLICA", valor=pas, unidade="mmHg", aferido_em=quando),
            Medicao(cidadao_id=joao.id, tipo="PA_DIASTOLICA", valor=pad, unidade="mmHg", aferido_em=quando),
            Medicao(cidadao_id=joao.id, tipo="PESO", valor=peso, unidade="kg", aferido_em=quando),
        ])

    # Cidadão 2: criança, quadro respiratório
    lucas = Cidadao(
        nome_completo="Lucas Andrade Souza", cpf="55566677788",
        cns="700500600700800", data_nascimento=date(2019, 7, 2), sexo="M",
        nome_mae="Fernanda Souza", telefone="(27) 98888-2020",
        endereco="Av. Beira Rio, 1200 - São Pedro",
    )
    db.add(lucas)
    db.flush()

    # Cidadão 3: gestante
    ana = Cidadao(
        nome_completo="Ana Clara Ribeiro", cpf="99988877766",
        cns="700900100200300", data_nascimento=date(1997, 11, 20), sexo="F",
        nome_mae="Cláudia Ribeiro", telefone="(27) 97777-3030",
        endereco="Rua do Sol, 88 - Jardim América",
    )
    db.add(ana)
    db.flush()

    # Atendimento histórico finalizado (João)
    hist = Atendimento(
        cidadao_id=joao.id, profissional_id=med.id, criado_por_id=recep.id,
        status="FINALIZADO", tipo="RETORNO", motivo="Retorno de hipertensão",
        criado_em=agora - timedelta(days=90),
        inicio_atendimento=agora - timedelta(days=90),
        fim_atendimento=agora - timedelta(days=90) + timedelta(minutes=18),
        subjetivo="Assintomático. Refere boa adesão à medicação. Reduziu sal na dieta.",
        objetivo="BEG, corado, hidratado. PA 138x86 mmHg. Peso 79,8 kg. Ausculta cardiopulmonar normal.",
        avaliacao="Hipertensão essencial (I10) — controle parcial. DM2 (E11.9) — estável.",
        plano="Mantida medicação. Reforçada dieta hipossódica e caminhada 30 min/dia. Solicitados exames. Retorno em 3 meses.",
        desfecho="RETORNO_AGENDADO", retorno_data=(date.today() + timedelta(days=1)),
        assinado=True, assinado_em=agora - timedelta(days=90) + timedelta(minutes=18),
    )
    db.add(hist)

    # Fila de hoje (Passo 1)
    db.add_all([
        Atendimento(cidadao_id=joao.id, criado_por_id=recep.id, status="AGUARDANDO",
                    tipo="RETORNO", motivo="Retorno + resultado de exames",
                    classificacao_risco="VERDE"),
        Atendimento(cidadao_id=lucas.id, criado_por_id=recep.id, status="AGUARDANDO",
                    tipo="CONSULTA", motivo="Tosse e febre há 2 dias",
                    classificacao_risco="AMARELO"),
        Atendimento(cidadao_id=ana.id, criado_por_id=recep.id, status="AGUARDANDO",
                    tipo="CONSULTA", motivo="Pré-natal - 1ª consulta",
                    classificacao_risco="AZUL"),
    ])
    db.commit()
    print("[bootstrap] usuários e dados de exemplo criados (senha: 123456)")


# colunas adicionadas após a criação inicial (migração leve, Postgres)
_MIGRACOES = [
    "ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS acolhimento TEXT",
    "ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS acolhido_por_id UUID REFERENCES usuarios(id)",
    "ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS acolhido_em TIMESTAMPTZ",
    "ALTER TABLE encaminhamentos ADD COLUMN IF NOT EXISTS tipo VARCHAR(28) DEFAULT 'CONSULTA_ESPECIALIZADA'",
    "ALTER TABLE encaminhamentos ADD COLUMN IF NOT EXISTS cid VARCHAR(10)",
]


def _migrar() -> None:
    with engine.begin() as conn:
        for sql in _MIGRACOES:
            try:
                conn.exec_driver_sql(sql)
            except Exception as e:  # tabela ainda não existe: create_all cuida
                print(f"[migração] {sql[:50]}… -> {e}")


def inicializar() -> None:
    Base.metadata.create_all(bind=engine)
    _migrar()
    with SessionLocal() as db:
        _seed_catalogos(db)
        _seed_demo(db)
