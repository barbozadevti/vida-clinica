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
  rastreabilidade do prontuário (log de auditoria — Onda 7).
- **Personas:** Recepção, Enfermagem, Médico(a) e Administrador(a) — os quatro
  perfis de login do sistema.
- **MVP 1 — Prontuário digital do atendimento** (10/09): login/perfis, fila,
  acolhimento, SOAP, documentos em PDF, finalização com assinatura.
- **MVP 2 — Fechamento financeiro do dia** (12/09): agenda, convênios,
  financeiro com nota fiscal em PDF, estoque com alerta.
- **Ondas 4 e 5 (16/09):** confirmação de agendamento por WhatsApp, portal do
  paciente, teleconsulta, guia TISS simplificada e multiclínica — ver seção
  [Ondas 4 a 7](#ondas-4-a-7--próximo-incremento-validado) abaixo.
- **Onda 6 (18/09):** direcionar o atendimento a um profissional específico
  ("trocar de médico"), nota fiscal (PF/PJ) substituindo o recibo, emissão
  separada por setor financeiro com envio por WhatsApp/e-mail.
- **Onda 7 (19/09):** log de auditoria (LGPD) — rastreabilidade de acesso ao
  prontuário. App mobile segue como próxima hipótese a validar.

> Projeto pessoal full-stack — modelagem de dados, API REST documentada (Swagger),
> regras de negócio de uma clínica real (agenda, convênios, financeiro, estoque,
> prontuário) e front-end funcional do zero. O fluxo de atendimento (fila → folha de
> rosto → SOAP → documentos → finalização) é inspirado no e-SUS PEC, usado nas UBS
> brasileiras, generalizado aqui para o contexto de uma clínica/consultório privado.

## Funcionalidades

| Módulo | O que faz |
|---|---|
| **Agenda** | Marcação de consultas por profissional, data e horário; confirmação, falta e cancelamento; "paciente chegou" envia direto para a fila do dia. |
| **Atendimento do dia (fila)** | Fila ordenada por classificação de risco (Manchester); acolhimento da enfermagem com sinais vitais; a recepção pode direcionar o atendimento a um profissional específico ("trocar de médico") — só ele (ou o ADMIN) consegue **Atender**; o prontuário abre com os vitais já pré-preenchidos. |
| **Prontuário — folha de rosto** | Alergias em destaque, medicamentos em uso, histórico de consultas e **gráficos de evolução** (PA, peso, IMC, glicemia). |
| **Prontuário — SOAP** | Registro clínico em 4 blocos (Subjetivo/Objetivo/Avaliação/Plano) com sinais vitais estruturados e busca de diagnóstico por **CID-10 / CIAP-2**. |
| **Documentos clínicos** | Receituário, atestado (texto gerado automaticamente), requisição de exames e guia de encaminhamento — **inclusive para avaliação cirúrgica** — todos em **PDF real**, além de impressão direta A4. |
| **Financeiro** | Lançamento de cobranças (dinheiro, PIX, cartão débito/crédito, convênio, boleto), baixa de pagamento, **nota fiscal de serviço em PDF** (PF ou PJ, numeração sequencial, emissão restrita ao setor financeiro/recepção) com envio por WhatsApp/e-mail, resumo por período e por forma de pagamento. |
| **Convênios** | Cadastro de convênios/planos de saúde vinculados ao paciente (carteirinha, registro ANS). |
| **Estoque** | Itens de medicamentos/materiais/insumos com quantidade mínima, entradas/saídas/ajustes com histórico e **alerta visual de estoque baixo**. |
| **Pacientes** | Cadastro completo, ficha com alergias, medicamentos em uso e linha do tempo de atendimentos. |
| **Retornos** | Lista de retornos agendados; recepção recoloca o paciente na fila com um clique. |
| **Relatórios** | Produção por profissional, desfecho, risco e CID/CIAP mais frequentes, com exportação em **PDF** e **Excel** (abas por dimensão + gráficos, estilo painel de BI). |
| **Painel** | Visão geral do dia: agendamentos, fila, faturamento, estoque baixo e produção por profissional. |
| **Usuários** | Cadastro/edição de usuários e perfis pelo ADMIN, com unidade de lotação. |
| **Unidades (multiclínica)** | Cadastro de unidades/filiais; cada usuário pertence a uma unidade e só vê fila, agenda, relatórios e painel da própria unidade — o ADMIN pode ver tudo ou filtrar por unidade. |
| **Portal do paciente** | Página própria (`/portal`) onde o paciente vê seus agendamentos e baixa seus documentos, sem precisar de senha. |
| **App instalável (PWA)** | O app da equipe e o portal do paciente podem ser **instalados no celular** (ícone na tela inicial, tela cheia, funciona com internet instável) direto pelo navegador, sem loja de app. |
| **Auditoria (LGPD)** | Log de quem acessou/alterou o quê — login, visualização de paciente/atendimento, edição do SOAP, finalização/reabertura de atendimento, emissão de documento e de nota fiscal. Consulta filtrável por período/usuário/paciente/ação, restrita ao ADMIN. |

### Ondas 4 a 7 — próximo incremento validado

Fatia mínima de cada ideia, para validar a hipótese sem construir a integração completa (o "M" de MVP):

| Onda | O que foi feito | Limite conhecido (próximo passo real) |
|---|---|---|
| **Confirmação por WhatsApp** | Botão na Agenda que abre o WhatsApp com a mensagem pronta (link `wa.me`, sem custo) | Não é a API oficial do WhatsApp Business — a recepção envia manualmente, não há confirmação automática de volta |
| **Portal do paciente** | Página `/portal`: login por CPF + nascimento, vê agendamentos futuros e baixa seus próprios documentos em PDF | Autenticação simples demais para produção real — trocar por SMS/e-mail com código de uso único |
| **Teleconsulta** | Agendamento tipo "Teleconsulta" gera uma sala de vídeo (Jitsi Meet, gratuito) | Sem gravação, sem sala de espera virtual, sem integração com prontuário durante a chamada |
| **Guia TISS** | PDF simplificado com os campos de uma guia de consulta (beneficiário, prestador, procedimento, CID) | Não é o XML eletrônico que a ANS exige para envio às operadoras — é o documento, não a integração de faturamento |
| **Multiclínica** | Cadastro de unidades/filiais; fila, agenda, relatórios e painel filtrados por unidade (ADMIN vê tudo ou filtra); documentos impressos usam o timbre da unidade do atendimento | Estoque e faturamento do painel ainda são globais — esses módulos não têm `unidade_id` |
| **App mobile (PWA)** | Manifest + service worker: "Adicionar à tela inicial" no Android/iOS, ícone e splash próprios, abre em tela cheia (sem barra do navegador), shell da aplicação funciona com rede instável | Não é um app nativo (sem push notification real, sem acesso a APIs do aparelho) — é a fatia mais fina possível da hipótese "app mobile", sem custo de loja nem build nativo |
| **Trocar de médico** | Ao adicionar à fila (ou agendar), dá pra escolher um profissional específico; só ele (ou o ADMIN) consegue clicar Atender — bloqueia com mensagem clara quem tentar assumir a consulta de outro | Preferência vale só para o dia; não existe agenda de "médico titular" do paciente entre visitas |
| **Nota fiscal (PF/PJ)** | Substitui o recibo: numeração sequencial, tomador PF (CPF do paciente) ou PJ (CNPJ do convênio), emissão restrita ao financeiro/recepção, botões de envio por WhatsApp/e-mail | Documento interno simplificado — não é a NFS-e eletrônica oficial, que é transmitida à parte pela Secretaria Municipal da Fazenda |
| **Auditoria (LGPD)** | Log de acesso a dado sensível de saúde: login, visualização e edição de paciente/atendimento, emissão de documento/nota fiscal — consulta por período/usuário/paciente, restrita ao ADMIN | Não gera alerta em tempo real nem exporta relatório de conformidade — é a consulta mínima para provar rastreabilidade |

### O fluxo de atendimento (prontuário)

1. **Fila do dia** — recepção adiciona o paciente; enfermagem faz o **acolhimento**
   (sinais vitais + risco); o profissional clica **Atender**.
2. **Folha de rosto** — alergias, medicamentos em uso, histórico e gráficos de evolução.
3. **SOAP** — Subjetivo, Objetivo (vitais + exame físico), Avaliação (CID-10/CIAP-2), Plano.
4. **Documentos** — prescrição, atestado, requisição de exames (impressão + PDF).
5. **Finalização** — desfecho (alta / retorno / encaminhamento / observação) e assinatura;
   o prontuário é bloqueado e o paciente sai da fila.

### Documentos em PDF (layout de formulário, cabeçalho da clínica)

Receituário (simples ou controle especial) · Atestado médico · Requisição de Exames ·
Guia de Encaminhamento (consulta especializada, avaliação cirúrgica, exames
especializados ou urgência) · Resumo do Atendimento · Guia TISS simplificada ·
**Nota Fiscal de Serviço** (PF/PJ).

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

### "PostgreSQL não respondeu" / "Deseja finalizar o arquivo em lotes (S/N)?"

**Causa raiz:** o PostgreSQL aqui roda como um processo comum (não como serviço
do Windows). Quando o computador desliga, o Windows o mata sem aviso — então
**toda inicialização seguinte faz uma recuperação automática** (conferir ~4.000
arquivos, com o antivírus no meio: 30 a 90 s). Isso é normal e os dados ficam
protegidos pelo log de transações (WAL).

O que *piorava* tudo (corrigido em `ABRIR e-SUS.bat` + `scripts\pg.ps1`): o banco
nascia **dentro da janela do atalho**, então um Ctrl+C (o "Deseja finalizar o
arquivo em lotes?") ou fechar a janela também derrubava o banco no meio da
recuperação, e cada novo clique reiniciava a recuperação do zero. Agora:

- o banco sobe em **janela própria e oculta** — Ctrl+C / fechar o atalho não o atingem;
- um banco que está só **recuperando** nunca é derrubado (clicar de novo apenas espera);
- só se limpa processo/trava órfã quando nada saudável está rodando;
- ao encerrar o sistema, o banco é desligado de forma limpa.

**Solução definitiva (uma vez só):** dar dois cliques em
**`INSTALAR SERVICO DO BANCO.bat`** e clicar **Sim** no pedido de administrador do
Windows. Ele registra o PostgreSQL como **serviço do Windows**: o Windows o
desliga direito antes de desligar o PC (acaba a recuperação) e o liga sozinho no
boot. Ele mesmo dá à conta de serviços acesso às pastas do banco, confere que o
banco respondeu e, se algo falhar, **desfaz tudo** (o atalho segue funcionando).
Depois disso o `pg.ps1`/atalho detectam o serviço e só esperam por ele.

Para desfazer um dia: pare o serviço `PostgresVidaClinica` em "Serviços" e rode
`& "C:\Users\rafap\pgsql\bin\pg_ctl.exe" unregister -N "PostgresVidaClinica"`.

(O instalador é um script para *você* rodar, de propósito: registrar serviço e
mexer em permissões é mudança de configuração do sistema, que exige
administrador e cabe a você aprovar.)

## Testes automatizados

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -v
```

Roda contra um banco isolado (`esus_test`, criado uma vez com
`psql -U postgres -c "CREATE DATABASE esus_test;"`), zerado e re-semeado a
cada teste com o mesmo `bootstrap.py` de produção — não toca no banco `esus`
usado pelo atalho. 43 testes cobrindo autenticação/permissões por perfil,
validação de cadastro de paciente, filtro multiclínica (fila, agenda e
relatórios por unidade), trocar de médico (fila e chegada por agendamento),
nota fiscal (PF/PJ, numeração sequencial, restrição por perfil) e auditoria
(log de acesso por ação/paciente/usuário).

## Usuários de teste (senha `123456`)

| E-mail | Perfil | Unidade |
|---|---|---|
| `medico@ubs.local` | MÉDICO (Dr. Victor Dalvi) | Centro |
| `enfermagem@ubs.local` | ENFERMEIRO | Centro |
| `recepcao@ubs.local` | RECEPÇÃO | Centro |
| `medico.sul@ubs.local` | MÉDICO (Dra. Camila Duarte) | Sul |
| `recepcao.sul@ubs.local` | RECEPÇÃO | Sul |
| `katia@ubs.local` | MÉDICO (Dra. Katia de Mello Portinho — otorrinolaringologia) | Centro |
| `admin@ubs.local` | ADMIN | todas |

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
│   ├── auditoria.py       # Onda 7 — helper de log de acesso (LGPD)
│   └── routers/
│       ├── core/          # auth, usuarios, catalogos, relatorios, auditoria
│       ├── prontuario/    # MVP 1 — cidadaos, fila, atendimentos, documentos
│       ├── gestao/        # MVP 2 — agenda, convenios, financeiro, estoque
│       └── expansao/      # Ondas 4/5 — unidades (multiclínica), portal do paciente
├── backend/tests/         # pytest — auth/permissões, cadastro de paciente, multiclínica,
│                          # trocar de médico, nota fiscal, auditoria
├── frontend/
│   ├── index.html         # sistema da equipe
│   ├── portal.html        # portal do paciente (mini-app à parte)
│   ├── manifest.json / portal-manifest.json  # Onda 6 — PWA (cada um com seu start_url)
│   ├── sw.js              # Onda 6 — service worker (shell da app, nunca cacheia /api/)
│   └── assets/
│       ├── styles.css
│       ├── icons/          # ícones do PWA (gerados por scripts/gen_icons.py)
│       └── js/
│           ├── core.js        # infra, auth, navegação, painel, cidadãos, usuários, auditoria
│           ├── prontuario.js  # MVP 1 — fila, acolhimento, SOAP, documentos, retornos
│           ├── gestao.js      # MVP 2 — agenda (+WhatsApp/teleconsulta), convênios, financeiro (+TISS), estoque, relatórios
│           ├── expansao.js    # Ondas 4/5 — unidades (multiclínica)
│           ├── portal.js      # lógica do portal do paciente
│           └── boot.js        # inicializa a sessão (carregado por último)
├── scripts/               # pg.ps1, reset_db.ps1, gen_icons.py
├── Dockerfile + render.yaml   # deploy na nuvem (Render), opcional
├── INSTALAR SERVICO DO BANCO.bat   # opcional, 1 vez: banco vira serviço do Windows (pede admin)
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
- WhatsApp, teleconsulta, guia TISS, nota fiscal e portal do paciente são fatias
  mínimas (MVP) para validar a ideia — ver limites conhecidos na tabela "Ondas 4 a 7"
  acima antes de usar em produção com dados reais.
