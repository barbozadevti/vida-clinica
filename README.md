# 💠 Vida+ Clínica — Sistema de Gestão Clínica

Sistema completo de gestão para clínicas e consultórios: **agenda**, **recepção/fila**,
**prontuário eletrônico** com fluxo clínico SOAP, **prescrição/atestado/exames em PDF**,
**financeiro** (particular e convênios) e **estoque** — com login e perfis de acesso
desde o primeiro dia.

**Stack:** FastAPI (Python) + PostgreSQL (SQLAlchemy 2.0) · frontend HTML/CSS/JS puro
(sem framework, sem build) · autenticação JWT + bcrypt · geração de PDF com xhtml2pdf ·
perfis **MÉDICO, ENFERMEIRO, RECEPÇÃO, ADMIN**, cada um vendo só o que precisa ver.

## Estratégia de produto (Lean Inception)

O produto foi (re)lido com o método **Lean Inception**, de Paulo Caroli: visão do
produto, personas, jornadas, sequenciador de funcionalidades e canvas MVP — o
documento completo está publicado à parte. Resumo:

- **Objetivos:** reduzir o tempo administrativo da recepção e da equipe clínica ·
  ter controle financeiro confiável do caixa do dia · garantir segurança e
  rastreabilidade do prontuário.
- **Personas:** Recepção, Enfermagem, Médico(a) e Administrador(a) — os quatro
  perfis de login do sistema.
- **MVP 1 — Prontuário digital do atendimento** (10/09): login/perfis, fila,
  acolhimento, SOAP, documentos em PDF, finalização com assinatura.
- **MVP 2 — Fechamento financeiro do dia** (12/09): agenda, convênios,
  financeiro com recibo em PDF, estoque com alerta.
- **Ondas 4 e 5 (16/09):** confirmação de agendamento por WhatsApp, portal do
  paciente, teleconsulta, guia TISS simplificada e multiclínica — ver seção
  [Ondas 4 e 5](#ondas-4-e-5--próximo-incremento-validado) abaixo. App mobile
  segue como próxima hipótese a validar.

> Projeto pessoal full-stack — modelagem de dados, API REST documentada (Swagger),
> regras de negócio de uma clínica real (agenda, convênios, financeiro, estoque,
> prontuário) e front-end funcional do zero. O fluxo de atendimento (fila → folha de
> rosto → SOAP → documentos → finalização) é inspirado no e-SUS PEC, usado nas UBS
> brasileiras, generalizado aqui para o contexto de uma clínica/consultório privado.

## Funcionalidades

| Módulo | O que faz |
|---|---|
| **Agenda** | Marcação de consultas por profissional, data e horário; confirmação, falta e cancelamento; "paciente chegou" envia direto para a fila do dia. |
| **Atendimento do dia (fila)** | Fila ordenada por classificação de risco (Manchester); acolhimento da enfermagem com sinais vitais; o profissional clica **Atender** e abre o prontuário com os vitais já pré-preenchidos. |
| **Prontuário — folha de rosto** | Alergias em destaque, medicamentos em uso, histórico de consultas e **gráficos de evolução** (PA, peso, IMC, glicemia). |
| **Prontuário — SOAP** | Registro clínico em 4 blocos (Subjetivo/Objetivo/Avaliação/Plano) com sinais vitais estruturados e busca de diagnóstico por **CID-10 / CIAP-2**. |
| **Documentos clínicos** | Receituário, atestado (texto gerado automaticamente), requisição de exames e guia de encaminhamento — **inclusive para avaliação cirúrgica** — todos em **PDF real**, além de impressão direta A4. |
| **Financeiro** | Lançamento de cobranças (dinheiro, PIX, cartão débito/crédito, convênio, boleto), baixa de pagamento, **recibo em PDF**, resumo por período e por forma de pagamento. |
| **Convênios** | Cadastro de convênios/planos de saúde vinculados ao paciente (carteirinha, registro ANS). |
| **Estoque** | Itens de medicamentos/materiais/insumos com quantidade mínima, entradas/saídas/ajustes com histórico e **alerta visual de estoque baixo**. |
| **Pacientes** | Cadastro completo, ficha com alergias, medicamentos em uso e linha do tempo de atendimentos. |
| **Retornos** | Lista de retornos agendados; recepção recoloca o paciente na fila com um clique. |
| **Relatórios** | Produção por profissional, desfecho, risco e CID/CIAP mais frequentes, com exportação em **PDF** e **Excel** (abas por dimensão + gráficos, estilo painel de BI). |
| **Painel** | Visão geral do dia: agendamentos, fila, faturamento, estoque baixo e produção por profissional. |
| **Usuários** | Cadastro/edição de usuários e perfis pelo ADMIN, com unidade de lotação. |
| **Unidades (multiclínica)** | Cadastro de unidades/filiais; cada usuário pertence a uma unidade. |
| **Portal do paciente** | Página própria (`/portal`) onde o paciente vê seus agendamentos e baixa seus documentos, sem precisar de senha. |

### Ondas 4 e 5 — próximo incremento validado

Fatia mínima de cada ideia, para validar a hipótese sem construir a integração completa (o "M" de MVP):

| Onda | O que foi feito | Limite conhecido (próximo passo real) |
|---|---|---|
| **Confirmação por WhatsApp** | Botão na Agenda que abre o WhatsApp com a mensagem pronta (link `wa.me`, sem custo) | Não é a API oficial do WhatsApp Business — a recepção envia manualmente, não há confirmação automática de volta |
| **Portal do paciente** | Página `/portal`: login por CPF + nascimento, vê agendamentos futuros e baixa seus próprios documentos em PDF | Autenticação simples demais para produção real — trocar por SMS/e-mail com código de uso único |
| **Teleconsulta** | Agendamento tipo "Teleconsulta" gera uma sala de vídeo (Jitsi Meet, gratuito) | Sem gravação, sem sala de espera virtual, sem integração com prontuário durante a chamada |
| **Guia TISS** | PDF simplificado com os campos de uma guia de consulta (beneficiário, prestador, procedimento, CID) | Não é o XML eletrônico que a ANS exige para envio às operadoras — é o documento, não a integração de faturamento |
| **Multiclínica** | Cadastro de unidades/filiais; cada usuário pertence a uma | Agenda, fila e relatórios ainda são globais — falta filtrar por unidade |

### O fluxo de atendimento (prontuário)

1. **Fila do dia** — recepção adiciona o paciente; enfermagem faz o **acolhimento**
   (sinais vitais + risco); o profissional clica **Atender**.
2. **Folha de rosto** — alergias, medicamentos em uso, histórico e gráficos de evolução.
3. **SOAP** — Subjetivo, Objetivo (vitais + exame físico), Avaliação (CID-10/CIAP-2), Plano.
4. **Documentos** — prescrição, atestado, requisição de exames (impressão + PDF).
5. **Finalização** — desfecho (alta / retorno / encaminhamento / observação) e assinatura;
   o prontuário é bloqueado e o paciente sai da fila.

### Documentos em PDF (layout de formulário, cabeçalho da clínica)

Receituário · Atestado médico · Requisição de Exames · Guia de Encaminhamento
(consulta especializada, avaliação cirúrgica, exames especializados ou urgência) ·
Resumo do Atendimento · **Recibo de Pagamento**.

## Rodar no PC

Duplo-clique em **`ABRIR e-SUS.bat`** (ou no atalho da área de trabalho). Ele sobe
o PostgreSQL + o sistema e abre o navegador em <http://127.0.0.1:8010>.
Para parar: feche a janela preta.

Manualmente:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\pg.ps1 start   # sobe o banco
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8010 --reload
```

- App da equipe: <http://127.0.0.1:8010>  ·  Portal do paciente: <http://127.0.0.1:8010/portal>
  ·  API (Swagger): `/docs`
- O banco `esus` se popula sozinho no primeiro start (usuários, catálogos, convênios,
  estoque, agenda, unidades e exemplos de cobranças).
- `scripts\reset_db.ps1` recria tudo do zero.  `scripts\pg.ps1 psql` abre o console SQL.

## Usuários de teste (senha `123456`)

| E-mail | Perfil |
|---|---|
| `medico@ubs.local` | MÉDICO |
| `enfermagem@ubs.local` | ENFERMEIRO |
| `recepcao@ubs.local` | RECEPÇÃO |
| `admin@ubs.local` | ADMIN |

Portal do paciente (<http://127.0.0.1:8010/portal>) — sem senha, entra com CPF + data de
nascimento. Exemplo: CPF `11122233344`, nascimento `14/03/1966` (João Batista Ferreira).

## Estrutura

A pasta `routers/` (backend) e `assets/js/` (frontend) são organizadas pelas
mesmas ondas do MVP identificadas na Lean Inception — `core` é transversal,
`prontuario` é o MVP 1 e `gestao` é o MVP 2:

```
esus/
├── backend/app/
│   ├── main.py            # app FastAPI + serve o frontend
│   ├── config.py          # .env: DATABASE_URL, JWT_SECRET, dados da clínica
│   ├── security.py        # bcrypt + JWT + guardas de perfil
│   ├── models.py          # tabelas SQLAlchemy (prontuário, agenda, financeiro, estoque…)
│   ├── schemas.py         # contratos Pydantic da API
│   ├── bootstrap.py       # create_all + migração leve + seed de demonstração
│   ├── catalogos_seed.py  # listas de CID-10, CIAP-2, medicamentos, exames
│   ├── impressao.py       # HTML A4 + PDF dos documentos (xhtml2pdf)
│   ├── planilha.py        # Excel/BI do relatório de produção (openpyxl)
│   └── routers/
│       ├── core/          # auth, usuarios, catalogos, relatorios
│       ├── prontuario/    # MVP 1 — cidadaos, fila, atendimentos, documentos
│       ├── gestao/        # MVP 2 — agenda, convenios, financeiro, estoque
│       └── expansao/      # Ondas 4/5 — unidades (multiclínica), portal do paciente
├── frontend/
│   ├── index.html         # sistema da equipe
│   ├── portal.html        # portal do paciente (mini-app à parte)
│   └── assets/
│       ├── styles.css
│       └── js/
│           ├── core.js        # infra, auth, navegação, painel, cidadãos, usuários
│           ├── prontuario.js  # MVP 1 — fila, acolhimento, SOAP, documentos, retornos
│           ├── gestao.js      # MVP 2 — agenda (+WhatsApp/teleconsulta), convênios, financeiro (+TISS), estoque, relatórios
│           ├── expansao.js    # Ondas 4/5 — unidades (multiclínica)
│           ├── portal.js      # lógica do portal do paciente
│           └── boot.js        # inicializa a sessão (carregado por último)
├── scripts/               # pg.ps1, reset_db.ps1
├── Dockerfile + render.yaml   # deploy na nuvem (Render), opcional
└── ABRIR e-SUS.bat
```

Front-end permanece sem framework nem build — os quatro arquivos JS dividem
o mesmo escopo global (carregados em `<script>` sequenciais no `index.html`),
só a organização em arquivos mudou.

## Publicar na nuvem (opcional)

1. Suba o repositório para o GitHub.
2. Em <https://render.com> → **New +** → **Blueprint** → escolha o repositório → **Apply**.
   Cria um PostgreSQL grátis + o serviço web; no 1º start o banco se popula sozinho.

## Notas

- Sem HTTPS/deploy local — uso interno/demonstração. Trocar `JWT_SECRET` no `.env`
  antes de expor publicamente.
- A assinatura do atendimento é um registro de responsabilidade (profissional + data/hora),
  não um certificado digital ICP-Brasil.
- Dados de pacientes, convênios e financeiro nesta demonstração são fictícios.
- WhatsApp, teleconsulta, guia TISS e portal do paciente são fatias mínimas (MVP) para
  validar a ideia — ver limites conhecidos na tabela "Ondas 4 e 5" acima antes de
  usar em produção com dados reais.
