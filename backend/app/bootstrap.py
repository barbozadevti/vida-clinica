"""Cria as tabelas e popula dados iniciais quando o banco está vazio."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, text

from . import catalogos_seed as cat
from .database import Base, SessionLocal, engine
from .models import (
    Agendamento,
    Alergia,
    Atendimento,
    CatalogoCID,
    CatalogoCIAP,
    CatalogoExame,
    CatalogoMedicamento,
    Cidadao,
    Cobranca,
    Convenio,
    ItemEstoque,
    Medicao,
    MedicamentoEmUso,
    Prescricao,
    ProblemaAtendimento,
    Unidade,
    Usuario,
)
from .security import hash_senha


def _seed_catalogos(db) -> None:
    """Incremental (por código/nome), não "tudo ou nada": permite acrescentar
    itens novos em catalogos_seed.py (ex.: exames de otorrino) e eles
    aparecerem num banco que já tinha os catálogos antigos, sem precisar
    resetar."""
    existentes_cid = {c for (c,) in db.execute(select(CatalogoCID.codigo))}
    db.add_all(CatalogoCID(codigo=c, descricao=d) for c, d in cat.CID10 if c not in existentes_cid)

    existentes_ciap = {c for (c,) in db.execute(select(CatalogoCIAP.codigo))}
    db.add_all(CatalogoCIAP(codigo=c, descricao=d) for c, d in cat.CIAP2 if c not in existentes_ciap)

    existentes_med = {n for (n,) in db.execute(select(CatalogoMedicamento.nome))}
    db.add_all(CatalogoMedicamento(nome=n, principio_ativo=p, apresentacao=a, posologia_usual=pu)
              for n, p, a, pu in cat.MEDICAMENTOS if n not in existentes_med)
    # backfill: medicamento que já existia antes da posologia_usual existir
    posologia_por_nome = {n: pu for n, _, _, pu in cat.MEDICAMENTOS}
    for med in db.scalars(select(CatalogoMedicamento).where(CatalogoMedicamento.posologia_usual.is_(None))):
        if med.nome in posologia_por_nome:
            med.posologia_usual = posologia_por_nome[med.nome]

    existentes_exame = {n for (n,) in db.execute(select(CatalogoExame.nome))}
    db.add_all(CatalogoExame(nome=n, sinonimia=s) for n, s in cat.EXAMES if n not in existentes_exame)

    db.commit()


def _seed_convenios(db) -> dict[str, Convenio]:
    if db.scalar(select(Convenio).limit(1)):
        return {c.nome: c for c in db.scalars(select(Convenio))}
    convenios = [
        Convenio(nome="Unimed Regional", registro_ans="123456"),
        Convenio(nome="Bradesco Saúde", registro_ans="234567"),
        Convenio(nome="SulAmérica Saúde", registro_ans="345678"),
    ]
    db.add_all(convenios)
    db.commit()
    return {c.nome: c for c in convenios}


def _seed_unidades(db) -> dict[str, Unidade]:
    if db.scalar(select(Unidade).limit(1)):
        return {u.nome: u for u in db.scalars(select(Unidade))}
    unidades = [
        Unidade(nome="Vida+ Clínica — Unidade Centro", endereco="Rua da Saúde, 100 - Centro",
               telefone="(27) 3000-0000"),
        Unidade(nome="Vida+ Clínica — Unidade Sul", endereco="Av. Sul, 500 - Bairro Sul",
               telefone="(27) 3000-0001"),
    ]
    db.add_all(unidades)
    db.commit()
    return {u.nome: u for u in unidades}


def _seed_estoque(db) -> None:
    if db.scalar(select(ItemEstoque).limit(1)):
        return
    db.add_all([
        ItemEstoque(nome="Seringa descartável 5ml", categoria="MATERIAL", unidade="un",
                   quantidade=120, quantidade_minima=30),
        ItemEstoque(nome="Álcool 70% 1L", categoria="INSUMO", unidade="frasco",
                   quantidade=25, quantidade_minima=10),
        ItemEstoque(nome="Luva de procedimento (par)", categoria="MATERIAL", unidade="par",
                   quantidade=200, quantidade_minima=50),
        ItemEstoque(nome="Paracetamol 500mg", categoria="MEDICAMENTO", unidade="comprimido",
                   quantidade=8, quantidade_minima=20),
        ItemEstoque(nome="Máscara cirúrgica", categoria="MATERIAL", unidade="un",
                   quantidade=15, quantidade_minima=100),
        ItemEstoque(nome="Gaze estéril (pacote)", categoria="INSUMO", unidade="pacote",
                   quantidade=40, quantidade_minima=15),
    ])
    db.commit()


def _seed_demo(db) -> None:
    if db.scalar(select(Usuario).limit(1)):
        return

    convenios = _seed_convenios(db)
    unidades = _seed_unidades(db)
    centro = unidades["Vida+ Clínica — Unidade Centro"].id
    sul = unidades["Vida+ Clínica — Unidade Sul"].id

    admin = Usuario(nome="Administrador", email="admin@ubs.local",
                    senha_hash=hash_senha("123456"), perfil="ADMIN")
    recep = Usuario(nome="Joana Recepção", email="recepcao@ubs.local",
                    senha_hash=hash_senha("123456"), perfil="RECEPCAO", cbo="422105",
                    unidade_id=centro)
    enf = Usuario(nome="Enf. Paulo Lima", email="enfermagem@ubs.local",
                  senha_hash=hash_senha("123456"), perfil="ENFERMEIRO",
                  conselho="COREN 123456-ES", cbo="223505", unidade_id=centro)
    med = Usuario(nome="Dr. Victor Dalvi", email="medico@ubs.local",
                  senha_hash=hash_senha("123456"), perfil="MEDICO",
                  conselho="CRM 54321-ES", cbo="225125", cns="700000000000001",
                  unidade_id=centro)

    # Equipe da Unidade Sul (demonstra o filtro multiclínica)
    recep_sul = Usuario(nome="Renata Souza", email="recepcao.sul@ubs.local",
                        senha_hash=hash_senha("123456"), perfil="RECEPCAO", cbo="422105",
                        unidade_id=sul)
    med_sul = Usuario(nome="Dra. Camila Duarte", email="medico.sul@ubs.local",
                      senha_hash=hash_senha("123456"), perfil="MEDICO",
                      conselho="CRM 61234-ES", cbo="225125", cns="700000000000002",
                      unidade_id=sul)
    db.add_all([admin, recep, enf, med, recep_sul, med_sul])
    db.flush()

    agora = datetime.now(timezone.utc)

    # Cidadão 1: hipertenso + diabético, com alergia e histórico de PA/peso
    joao = Cidadao(
        nome_completo="João Batista Ferreira", cpf="11122233344",
        cns="700100200300400", data_nascimento=date(1966, 3, 14), sexo="M",
        nome_mae="Maria Ferreira", telefone="(27) 99999-1010",
        endereco="Rua das Palmeiras, 45 - Centro",
        convenio_id=convenios["Unimed Regional"].id, numero_carteirinha="0123456789012345",
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
        convenio_id=convenios["Bradesco Saúde"].id, numero_carteirinha="9988776655443322",
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

    # Cidadão 4: idosa, controle de diabetes (Unidade Centro)
    rosa = Cidadao(
        nome_completo="Rosa Maria Nascimento", cpf="22233344455",
        cns="700111222333444", data_nascimento=date(1954, 5, 9), sexo="F",
        nome_mae="Antônia Nascimento", telefone="(27) 99666-4040",
        endereco="Rua das Acácias, 210 - Centro",
        convenio_id=convenios["SulAmérica Saúde"].id, numero_carteirinha="5566778899001122",
    )
    db.add(rosa)
    db.flush()
    db.add_all([
        MedicamentoEmUso(cidadao_id=rosa.id, descricao="Metformina 850 mg",
                         posologia="1 comprimido no almoço e no jantar", via="oral", uso_continuo=True),
        MedicamentoEmUso(cidadao_id=rosa.id, descricao="Glibenclamida 5 mg",
                         posologia="1 comprimido antes do café", via="oral", uso_continuo=True),
    ])

    # Cidadão 5: adulto jovem com lombalgia (Unidade Sul)
    marcelo = Cidadao(
        nome_completo="Marcelo Tavares Costa", cpf="33344455566",
        cns="700222333444555", data_nascimento=date(1990, 8, 23), sexo="M",
        nome_mae="Ivone Costa", telefone="(27) 99555-5050",
        endereco="Av. Sul, 780 - Bairro Sul",
    )
    db.add(marcelo)
    db.flush()

    # Cidadão 6: criança com dermatite (Unidade Sul)
    isabela = Cidadao(
        nome_completo="Isabela Farias Moura", cpf="44455566677",
        cns="700333444555666", data_nascimento=date(2021, 2, 14), sexo="F",
        nome_mae="Patrícia Moura", telefone="(27) 99444-6060",
        endereco="Rua das Gaivotas, 33 - Bairro Sul",
        convenio_id=convenios["Bradesco Saúde"].id, numero_carteirinha="1122334455667788",
    )
    db.add(isabela)
    db.flush()

    # Atendimento histórico finalizado (João)
    hist = Atendimento(
        cidadao_id=joao.id, profissional_id=med.id, criado_por_id=recep.id,
        unidade_id=centro,
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
    db.flush()

    # Mais dois atendimentos finalizados recentes (para o Relatório de produção
    # já mostrar dados com o período padrão "mês atual")
    hist2 = Atendimento(
        cidadao_id=lucas.id, profissional_id=enf.id, criado_por_id=recep.id,
        unidade_id=centro,
        status="FINALIZADO", tipo="CONSULTA", motivo="Tosse e febre",
        classificacao_risco="AMARELO",
        criado_em=agora - timedelta(days=2), inicio_atendimento=agora - timedelta(days=2),
        fim_atendimento=agora - timedelta(days=2) + timedelta(minutes=12),
        subjetivo="Tosse produtiva e febre há 2 dias, sem outros sintomas.",
        objetivo="BEG, ativo, reativo. T 37,8°C. Ausculta pulmonar com poucos ruídos.",
        avaliacao="Infecção de vias aéreas superiores (J06.9).",
        plano="Sintomáticos, hidratação, retorno se piora.",
        desfecho="ALTA", assinado=True, assinado_em=agora - timedelta(days=2) + timedelta(minutes=12),
    )
    hist3 = Atendimento(
        cidadao_id=ana.id, profissional_id=med.id, criado_por_id=recep.id,
        unidade_id=centro,
        status="FINALIZADO", tipo="CONSULTA", motivo="Pré-natal",
        classificacao_risco="AZUL",
        criado_em=agora - timedelta(days=5), inicio_atendimento=agora - timedelta(days=5),
        fim_atendimento=agora - timedelta(days=5) + timedelta(minutes=25),
        subjetivo="Gestante, 1ª consulta de pré-natal, sem queixas.",
        objetivo="BEG. PA 110x70 mmHg. Altura uterina compatível com IG.",
        avaliacao="Gestação confirmada, 1º trimestre (Z34.0).",
        plano="Solicitados exames de rotina do pré-natal. Retorno em 30 dias.",
        desfecho="RETORNO_AGENDADO", retorno_data=(date.today() + timedelta(days=25)),
        assinado=True, assinado_em=agora - timedelta(days=5) + timedelta(minutes=25),
    )

    # Atendimentos finalizados da Unidade Sul (para o relatório/painel comparar unidades)
    hist4 = Atendimento(
        cidadao_id=marcelo.id, profissional_id=med_sul.id, criado_por_id=recep_sul.id,
        unidade_id=sul,
        status="FINALIZADO", tipo="CONSULTA", motivo="Dor lombar após esforço",
        classificacao_risco="VERDE",
        criado_em=agora - timedelta(days=3), inicio_atendimento=agora - timedelta(days=3),
        fim_atendimento=agora - timedelta(days=3) + timedelta(minutes=15),
        subjetivo="Dor lombar há 3 dias após carregar peso, sem irradiação.",
        objetivo="BEG. Mobilidade preservada. Sem sinais de alarme.",
        avaliacao="Dorsalgia (M54.5).",
        plano="Analgesia, repouso relativo, retorno se persistir.",
        desfecho="ALTA", assinado=True, assinado_em=agora - timedelta(days=3) + timedelta(minutes=15),
    )
    hist5 = Atendimento(
        cidadao_id=isabela.id, profissional_id=med_sul.id, criado_por_id=recep_sul.id,
        unidade_id=sul,
        status="FINALIZADO", tipo="CONSULTA", motivo="Lesões de pele",
        classificacao_risco="VERDE",
        criado_em=agora - timedelta(days=1), inicio_atendimento=agora - timedelta(days=1),
        fim_atendimento=agora - timedelta(days=1) + timedelta(minutes=10),
        subjetivo="Mãe refere manchas avermelhadas e coceira há 4 dias.",
        objetivo="Lesões eritematosas em dobras, sem sinais de infecção secundária.",
        avaliacao="Dermatite atópica (L20.9).",
        plano="Hidratante e corticoide tópico de baixa potência. Retorno se piora.",
        desfecho="ALTA", assinado=True, assinado_em=agora - timedelta(days=1) + timedelta(minutes=10),
    )
    db.add_all([hist2, hist3, hist4, hist5])
    db.flush()
    db.add_all([
        ProblemaAtendimento(atendimento_id=hist2.id, sistema="CID10", codigo="J06.9",
                            descricao="Infecção aguda das vias aéreas superiores"),
        ProblemaAtendimento(atendimento_id=hist3.id, sistema="CID10", codigo="Z34.0",
                            descricao="Supervisão de gravidez normal, primeiro trimestre"),
        ProblemaAtendimento(atendimento_id=hist.id, sistema="CID10", codigo="I10",
                            descricao="Hipertensão essencial (primária)"),
        ProblemaAtendimento(atendimento_id=hist4.id, sistema="CID10", codigo="M54.5",
                            descricao="Dor lombar baixa"),
        ProblemaAtendimento(atendimento_id=hist5.id, sistema="CID10", codigo="L20.9",
                            descricao="Dermatite atópica não especificada"),
    ])

    # Fila de hoje (Passo 1) — Unidade Centro
    db.add_all([
        Atendimento(cidadao_id=joao.id, criado_por_id=recep.id, unidade_id=centro,
                    status="AGUARDANDO", tipo="RETORNO", motivo="Retorno + resultado de exames",
                    classificacao_risco="VERDE"),
        Atendimento(cidadao_id=lucas.id, criado_por_id=recep.id, unidade_id=centro,
                    status="AGUARDANDO", tipo="CONSULTA", motivo="Tosse e febre há 2 dias",
                    classificacao_risco="AMARELO"),
        Atendimento(cidadao_id=ana.id, criado_por_id=recep.id, unidade_id=centro,
                    status="AGUARDANDO", tipo="CONSULTA", motivo="Pré-natal - 1ª consulta",
                    classificacao_risco="AZUL"),
        Atendimento(cidadao_id=rosa.id, criado_por_id=recep.id, unidade_id=centro,
                    status="AGUARDANDO", tipo="RETORNO", motivo="Controle de diabetes",
                    classificacao_risco="VERDE"),
    ])

    # Fila de hoje (Passo 1) — Unidade Sul
    db.add_all([
        Atendimento(cidadao_id=marcelo.id, criado_por_id=recep_sul.id, unidade_id=sul,
                    status="AGUARDANDO", tipo="CONSULTA", motivo="Dor lombar não resolvida",
                    classificacao_risco="VERDE"),
        Atendimento(cidadao_id=isabela.id, criado_por_id=recep_sul.id, unidade_id=sul,
                    status="AGUARDANDO", tipo="RETORNO", motivo="Reavaliação de dermatite",
                    classificacao_risco="AZUL"),
    ])

    # Agenda (marcações futuras, Passo "Agenda")
    hoje = date.today()
    db.add_all([
        # Unidade Centro
        Agendamento(cidadao_id=joao.id, profissional_id=med.id, criado_por_id=recep.id,
                   unidade_id=centro,
                   data=hoje, hora="14:30", tipo="RETORNO", status="CONFIRMADO",
                   observacao="Retorno hipertensão"),
        Agendamento(cidadao_id=lucas.id, profissional_id=enf.id, criado_por_id=recep.id,
                   unidade_id=centro,
                   data=hoje, hora="15:00", tipo="CONSULTA", status="AGENDADO",
                   observacao="Puericultura"),
        Agendamento(cidadao_id=ana.id, profissional_id=med.id, criado_por_id=recep.id,
                   unidade_id=centro,
                   data=hoje + timedelta(days=1), hora="09:00", tipo="PRE_NATAL",
                   status="AGENDADO", observacao="Pré-natal - 2ª consulta"),
        Agendamento(cidadao_id=joao.id, profissional_id=med.id, criado_por_id=recep.id,
                   unidade_id=centro,
                   data=hoje + timedelta(days=2), hora="10:30", tipo="RETORNO",
                   status="AGENDADO", observacao="Retorno com exames"),
        Agendamento(cidadao_id=ana.id, profissional_id=med.id, criado_por_id=recep.id,
                   unidade_id=centro,
                   data=hoje + timedelta(days=3), hora="16:00", tipo="TELECONSULTA",
                   status="AGENDADO", observacao="Acompanhamento pré-natal por vídeo"),
        Agendamento(cidadao_id=rosa.id, profissional_id=med.id, criado_por_id=recep.id,
                   unidade_id=centro,
                   data=hoje + timedelta(days=1), hora="11:00", tipo="RETORNO",
                   status="AGENDADO", observacao="Controle de diabetes - retorno"),
        # Unidade Sul
        Agendamento(cidadao_id=marcelo.id, profissional_id=med_sul.id, criado_por_id=recep_sul.id,
                   unidade_id=sul,
                   data=hoje, hora="13:30", tipo="RETORNO", status="CONFIRMADO",
                   observacao="Retorno dor lombar"),
        Agendamento(cidadao_id=isabela.id, profissional_id=med_sul.id, criado_por_id=recep_sul.id,
                   unidade_id=sul,
                   data=hoje + timedelta(days=1), hora="10:00", tipo="CONSULTA",
                   status="AGENDADO", observacao="Reavaliação dermatológica"),
        Agendamento(cidadao_id=marcelo.id, profissional_id=med_sul.id, criado_por_id=recep_sul.id,
                   unidade_id=sul,
                   data=hoje + timedelta(days=2), hora="14:00", tipo="TELECONSULTA",
                   status="AGENDADO", observacao="Acompanhamento por vídeo"),
    ])

    # Financeiro (cobranças de exemplo)
    db.add_all([
        Cobranca(cidadao_id=joao.id, atendimento_id=hist.id, criado_por_id=recep.id,
                convenio_id=convenios["Unimed Regional"].id,
                descricao="Consulta — clínico geral", valor=180.00,
                forma_pagamento="CONVENIO", status="PAGO", codigo_tuss="10101012",
                pago_em=agora - timedelta(days=90)),
        Cobranca(cidadao_id=ana.id, criado_por_id=recep.id,
                descricao="Consulta — pré-natal (particular)", valor=150.00,
                forma_pagamento="PIX", status="PENDENTE"),
        Cobranca(cidadao_id=lucas.id, criado_por_id=recep.id,
                convenio_id=convenios["Bradesco Saúde"].id,
                descricao="Consulta — pediatria", valor=220.00,
                forma_pagamento="CONVENIO", status="PAGO", pago_em=agora),
        Cobranca(cidadao_id=joao.id, criado_por_id=recep.id,
                descricao="Curativo — procedimento ambulatorial", valor=60.00,
                forma_pagamento="CARTAO_DEBITO", status="PAGO", pago_em=agora),
        Cobranca(cidadao_id=rosa.id, atendimento_id=None, criado_por_id=recep.id,
                convenio_id=convenios["SulAmérica Saúde"].id,
                descricao="Consulta — clínico geral", valor=180.00,
                forma_pagamento="CONVENIO", status="PENDENTE"),
        Cobranca(cidadao_id=marcelo.id, atendimento_id=hist4.id, criado_por_id=recep_sul.id,
                descricao="Consulta — clínico geral (particular)", valor=160.00,
                forma_pagamento="PIX", status="PAGO", pago_em=agora - timedelta(days=3)),
        Cobranca(cidadao_id=isabela.id, atendimento_id=hist5.id, criado_por_id=recep_sul.id,
                convenio_id=convenios["Bradesco Saúde"].id,
                descricao="Consulta — pediatria", valor=220.00,
                forma_pagamento="CONVENIO", status="PAGO", pago_em=agora - timedelta(days=1)),
    ])
    db.commit()
    print("[bootstrap] usuários e dados de exemplo criados (senha: 123456)")


def _seed_otorrino(db) -> None:
    """Acrescenta a especialista em otorrinolaringologia — ao contrário de
    _seed_demo, roda toda vez (idempotente pelo e-mail) para não exigir reset
    do banco em quem já estava usando o sistema."""
    # e-mail antigo (genérico, "otorrino@") -> nome dela de verdade, sem
    # recriar o usuário (mantém senha, histórico de atendimentos etc.)
    antigo = db.scalar(select(Usuario).where(Usuario.email == "otorrino@ubs.local"))
    if antigo and not db.scalar(select(Usuario).where(Usuario.email == "katia@ubs.local")):
        antigo.email = "katia@ubs.local"
        db.commit()

    if db.scalar(select(Usuario).where(Usuario.email == "katia@ubs.local")):
        return
    centro = db.scalar(select(Unidade).where(Unidade.nome.like("%Centro%")))
    recep = db.scalar(select(Usuario).where(Usuario.perfil == "RECEPCAO", Usuario.unidade_id == (centro.id if centro else None)))
    if not centro or not recep:
        return  # banco ainda nem foi inicializado — _seed_demo cuida do resto no próximo start

    katia = Usuario(nome="Dra. Katia de Mello Portinho", email="katia@ubs.local",
                    senha_hash=hash_senha("123456"), perfil="MEDICO",
                    conselho="CRM 45210-ES", cbo="225151", cns="700000000000004",
                    unidade_id=centro.id)
    db.add(katia)
    db.flush()

    beatriz = Cidadao(
        nome_completo="Beatriz Lima Cardoso", cpf="66677788899",
        cns="700444555666777", data_nascimento=date(1985, 4, 22), sexo="F",
        nome_mae="Marta Cardoso", telefone="(27) 99333-7070",
        endereco="Rua das Orquídeas, 55 - Centro",
    )
    db.add(beatriz)
    db.flush()

    agora = datetime.now(timezone.utc)
    hist = Atendimento(
        cidadao_id=beatriz.id, profissional_id=katia.id, criado_por_id=recep.id,
        unidade_id=centro.id,
        status="FINALIZADO", tipo="CONSULTA", motivo="Dor facial e congestão nasal há 10 dias",
        classificacao_risco="VERDE",
        criado_em=agora - timedelta(days=4), inicio_atendimento=agora - timedelta(days=4),
        fim_atendimento=agora - timedelta(days=4) + timedelta(minutes=20),
        subjetivo="Dor em região de seios da face, secreção nasal purulenta e congestão há 10 dias, piora ao abaixar a cabeça.",
        objetivo="Dor à palpação de seios maxilares. Rinoscopia com secreção purulenta em meato médio. Ausculta pulmonar normal.",
        avaliacao="Sinusite aguda bacteriana (J01.9).",
        plano="Amoxicilina + clavulanato 875/125mg 12/12h por 10 dias. Lavagem nasal com solução salina 3x/dia. Retorno se não melhorar em 72h.",
        desfecho="RETORNO_AGENDADO", retorno_data=(date.today() + timedelta(days=3)),
        assinado=True, assinado_em=agora - timedelta(days=4) + timedelta(minutes=20),
    )
    db.add(hist)
    db.flush()
    db.add(ProblemaAtendimento(atendimento_id=hist.id, sistema="CID10", codigo="J01.9",
                                descricao="Sinusite aguda não especificada"))
    db.add(Prescricao(atendimento_id=hist.id, medicamento="Amoxicilina + Clavulanato 875/125mg",
                      posologia="1 comprimido de 12/12h por 10 dias", quantidade="20 comprimidos",
                      via="oral", duracao_dias=10))

    # fila de hoje: retorno de reavaliação, para aparecer já na demo
    db.add(Atendimento(cidadao_id=beatriz.id, criado_por_id=recep.id, unidade_id=centro.id,
                       status="AGUARDANDO", tipo="RETORNO", motivo="Retorno de sinusite — reavaliação",
                       classificacao_risco="VERDE"))

    db.commit()
    print("[bootstrap] Dra. Katia de Mello Portinho (otorrinolaringologia) adicionada")


# colunas adicionadas após a criação inicial (migração leve, Postgres)
_MIGRACOES = [
    "ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS acolhimento TEXT",
    "ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS acolhido_por_id UUID REFERENCES usuarios(id)",
    "ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS acolhido_em TIMESTAMPTZ",
    "ALTER TABLE encaminhamentos ADD COLUMN IF NOT EXISTS tipo VARCHAR(28) DEFAULT 'CONSULTA_ESPECIALIZADA'",
    "ALTER TABLE encaminhamentos ADD COLUMN IF NOT EXISTS cid VARCHAR(10)",
    "ALTER TABLE cidadaos ADD COLUMN IF NOT EXISTS convenio_id UUID REFERENCES convenios(id)",
    "ALTER TABLE cidadaos ADD COLUMN IF NOT EXISTS numero_carteirinha VARCHAR(40)",
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS unidade_id UUID REFERENCES unidades(id)",
    "ALTER TABLE cobrancas ADD COLUMN IF NOT EXISTS codigo_tuss VARCHAR(20)",
    "ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS unidade_id UUID REFERENCES unidades(id)",
    "ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS unidade_id UUID REFERENCES unidades(id)",
    "ALTER TABLE catalogo_medicamentos ADD COLUMN IF NOT EXISTS posologia_usual TEXT",
    # campos de texto livre "abertos" (sem limite de caractere) — só CPF, CNS
    # e sexo continuam com tamanho fixo, por serem formatos realmente fixos.
    # VARCHAR -> TEXT no Postgres é uma troca de metadado, sem reescrever a
    # tabela nem perder dado.
    "ALTER TABLE unidades ALTER COLUMN nome TYPE TEXT",
    "ALTER TABLE unidades ALTER COLUMN endereco TYPE TEXT",
    "ALTER TABLE unidades ALTER COLUMN telefone TYPE TEXT",
    "ALTER TABLE usuarios ALTER COLUMN nome TYPE TEXT",
    "ALTER TABLE usuarios ALTER COLUMN conselho TYPE TEXT",
    "ALTER TABLE convenios ALTER COLUMN nome TYPE TEXT",
    "ALTER TABLE convenios ALTER COLUMN telefone TYPE TEXT",
    "ALTER TABLE cidadaos ALTER COLUMN nome_completo TYPE TEXT",
    "ALTER TABLE cidadaos ALTER COLUMN nome_social TYPE TEXT",
    "ALTER TABLE cidadaos ALTER COLUMN nome_mae TYPE TEXT",
    "ALTER TABLE cidadaos ALTER COLUMN telefone TYPE TEXT",
    "ALTER TABLE cidadaos ALTER COLUMN endereco TYPE TEXT",
    "ALTER TABLE cidadaos ALTER COLUMN numero_carteirinha TYPE TEXT",
    "ALTER TABLE alergias ALTER COLUMN substancia TYPE TEXT",
    "ALTER TABLE alergias ALTER COLUMN reacao TYPE TEXT",
    "ALTER TABLE medicamentos_em_uso ALTER COLUMN descricao TYPE TEXT",
    "ALTER TABLE medicamentos_em_uso ALTER COLUMN posologia TYPE TEXT",
    "ALTER TABLE medicamentos_em_uso ALTER COLUMN via TYPE TEXT",
    "ALTER TABLE atendimentos ALTER COLUMN motivo TYPE TEXT",
    "ALTER TABLE atendimento_problemas ALTER COLUMN descricao TYPE TEXT",
    "ALTER TABLE prescricoes ALTER COLUMN medicamento TYPE TEXT",
    "ALTER TABLE prescricoes ALTER COLUMN posologia TYPE TEXT",
    "ALTER TABLE prescricoes ALTER COLUMN quantidade TYPE TEXT",
    "ALTER TABLE prescricoes ALTER COLUMN via TYPE TEXT",
    "ALTER TABLE prescricoes ALTER COLUMN observacao TYPE TEXT",
    "ALTER TABLE atestados ALTER COLUMN cid TYPE TEXT",
    "ALTER TABLE solicitacoes_exame ALTER COLUMN indicacao_clinica TYPE TEXT",
    "ALTER TABLE encaminhamentos ALTER COLUMN especialidade TYPE TEXT",
    "ALTER TABLE encaminhamentos ALTER COLUMN cid TYPE TEXT",
    "ALTER TABLE agendamentos ALTER COLUMN observacao TYPE TEXT",
    "ALTER TABLE cobrancas ALTER COLUMN descricao TYPE TEXT",
    "ALTER TABLE itens_estoque ALTER COLUMN nome TYPE TEXT",
    "ALTER TABLE movimentos_estoque ALTER COLUMN motivo TYPE TEXT",
    "ALTER TABLE catalogo_medicamentos ALTER COLUMN nome TYPE TEXT",
    "ALTER TABLE catalogo_medicamentos ALTER COLUMN principio_ativo TYPE TEXT",
    "ALTER TABLE catalogo_medicamentos ALTER COLUMN apresentacao TYPE TEXT",
    "ALTER TABLE catalogo_cid10 ALTER COLUMN descricao TYPE TEXT",
    "ALTER TABLE catalogo_ciap2 ALTER COLUMN descricao TYPE TEXT",
    "ALTER TABLE catalogo_exames ALTER COLUMN nome TYPE TEXT",
    "ALTER TABLE catalogo_exames ALTER COLUMN sinonimia TYPE TEXT",
    "ALTER TABLE atendimento_problemas ALTER COLUMN codigo DROP NOT NULL",
    "ALTER TABLE prescricoes ADD COLUMN IF NOT EXISTS controle_especial BOOLEAN NOT NULL DEFAULT false",
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
        _seed_estoque(db)
        _seed_demo(db)
        _seed_otorrino(db)
