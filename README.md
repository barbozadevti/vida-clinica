# e-SUS UBS — Prontuário / Atendimento (APS)

Sistema de **atendimento médico na Atenção Primária**, seguindo o fluxo padrão
da consulta (fila → folha de rosto → SOAP → documentos → finalização).

**Stack:** FastAPI + PostgreSQL (SQLAlchemy 2.0) · frontend HTML/CSS/JS sem build ·
autenticação JWT com perfis (MÉDICO, ENFERMEIRO, RECEPÇÃO, ADMIN).

## O fluxo do atendimento

| Passo | Tela | O que faz |
|---|---|---|
| **1. Lista de atendimento** | *Atendimento do dia* | Fila de cidadãos aguardando (ordenada por classificação de risco). A recepção adiciona à fila; a **enfermagem faz o acolhimento** (sinais vitais + classificação de risco de Manchester); o profissional clica **Atender** → status muda para *Em atendimento* e abre o prontuário. Os sinais vitais do acolhimento já vêm preenchidos no bloco O do SOAP. |
| **2. Folha de rosto** | topo do prontuário | **Alergias em vermelho**, medicamentos em uso, consultas anteriores e **gráficos de evolução** (pressão arterial, peso, IMC, glicemia). |
| **3. Registro clínico (SOAP)** | 4 blocos coloridos | **S** subjetivo (queixa) · **O** objetivo (sinais vitais estruturados: PA, peso, altura, temperatura, FC, SatO₂, glicemia + exame físico) · **A** avaliação (diagnóstico + busca de **CID-10 / CIAP-2**) · **P** plano/conduta. |
| **4. Prescrição e documentos** | abas | **Prescrever medicamentos** (busca na farmácia municipal), **Atestado** (texto gerado) e **Requisição de exames** (catálogo do SUS). Cada documento tem botão **Imprimir** (abre a folha A4 e chama a impressão) e **PDF** (baixa o arquivo). |
| **5. Finalização** | botão verde | Define o **desfecho** (Alta / Retorno / Encaminhamento / Observação) e **assina** → o prontuário fica bloqueado e o cidadão sai da fila. No encaminhamento escolhe-se o **tipo** (consulta especializada, **avaliação cirúrgica**, exames especializados, urgência). Documentos de saída em A4/PDF: **resumo do atendimento** e **guia de encaminhamento**. |

### Documentos gerados (A4 / PDF, layout de formulário SUS)

Receituário · Atestado médico · **Requisição de Exames — SUS** · **Guia de Encaminhamento**
(inclui a variante *para Avaliação Cirúrgica*) · Resumo do Atendimento.
Todos com cabeçalho da UBS, identificação do cidadão (nome, CNS, nascimento, mãe),
corpo em caixas e assinatura do profissional (nome, conselho, CBO, CNS).

### Além dos 5 passos

- **Retornos agendados** — aba com a lista de retornos previstos; a recepção coloca o cidadão de volta na fila com um clique.
- **Linha do tempo do cidadão** — na ficha, todos os atendimentos anteriores; clique para ver o SOAP completo (somente leitura).
- **Relatório de produção** — por profissional, desfecho, classificação de risco e CID/CIAP mais frequentes, com **exportação CSV** (para envio/consolidação).
- **Painel** — aguardando, sem acolhimento, em atendimento, finalizados hoje, retornos da semana e produção de cada profissional no dia.
- **Reabrir atendimento** — ADMIN pode reabrir um atendimento finalizado (registra o motivo no prontuário).

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

- App: <http://127.0.0.1:8010>  ·  API (Swagger): `/docs`
- O banco `esus` se popula sozinho no primeiro start (usuários + catálogos + exemplos).
- `scripts\reset_db.ps1` recria tudo do zero.  `scripts\pg.ps1 psql` abre o console SQL.

## Usuários de teste (senha `123456`)

| E-mail | Perfil |
|---|---|
| `medico@ubs.local` | MÉDICO |
| `enfermagem@ubs.local` | ENFERMEIRO |
| `recepcao@ubs.local` | RECEPÇÃO |
| `admin@ubs.local` | ADMIN |

## Estrutura

```
esus/
├── backend/app/
│   ├── main.py            # app FastAPI + serve o frontend
│   ├── config.py          # .env: DATABASE_URL, JWT_SECRET
│   ├── security.py        # bcrypt + JWT + guardas de perfil
│   ├── models.py          # tabelas SQLAlchemy
│   ├── schemas.py
│   ├── bootstrap.py       # create_all + migração leve + seed
│   ├── catalogos_seed.py  # listas de CID-10, CIAP-2, medicamentos, exames
│   ├── impressao.py       # HTML A4 dos documentos
│   └── routers/           # auth, usuarios, cidadaos, fila, atendimentos,
│                          # documentos, relatorios, catalogos
├── frontend/              # index.html + assets (app.js, styles.css)
├── scripts/               # pg.ps1, reset_db.ps1
├── Dockerfile + render.yaml   # deploy na nuvem (Render)
└── ABRIR e-SUS.bat
```

## Publicar na nuvem (opcional)

1. Suba o repositório para o GitHub.
2. Em <https://render.com> → **New +** → **Blueprint** → escolha o repositório → **Apply**.
   Cria um PostgreSQL grátis + o serviço web; no 1º start o banco se popula sozinho.

## Notas

- Sem HTTPS/deploy local — uso interno. Trocar `JWT_SECRET` no `.env` antes de expor.
- A assinatura é um registro de responsabilidade (profissional + data/hora), não
  certificado digital ICP-Brasil.
