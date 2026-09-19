from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ─────────── Auth / Usuários ───────────
class LoginIn(BaseModel):
    email: str
    senha: str


class UsuarioResumo(ORM):
    id: uuid.UUID
    nome: str
    perfil: str
    conselho: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResumo


# ─────────── Unidades (multiclínica) ───────────
class UnidadeIn(BaseModel):
    nome: str = Field(min_length=1)
    endereco: str | None = None
    telefone: str | None = None
    cnpj: str | None = Field(default=None, max_length=14)
    ativo: bool = True


class UnidadeOut(UnidadeIn, ORM):
    id: uuid.UUID
    criado_em: datetime


class UnidadeResumo(ORM):
    id: uuid.UUID
    nome: str


class UsuarioBase(BaseModel):
    nome: str = Field(min_length=1)
    email: str
    perfil: str
    cns: str | None = None
    cbo: str | None = None
    conselho: str | None = None
    unidade_id: uuid.UUID | None = None
    ativo: bool = True


class UsuarioCreate(UsuarioBase):
    senha: str = Field(min_length=4, max_length=72)


class UsuarioUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    perfil: str | None = None
    cns: str | None = None
    cbo: str | None = None
    conselho: str | None = None
    unidade_id: uuid.UUID | None = None
    ativo: bool | None = None
    senha: str | None = Field(default=None, min_length=4, max_length=72)


class UsuarioOut(UsuarioBase, ORM):
    id: uuid.UUID
    criado_em: datetime
    unidade: UnidadeResumo | None = None


# ─────────── Cidadão ───────────
# Só CPF e CNS têm tamanho fixo de verdade (11 e 15 dígitos); todo o resto é
# texto livre e fica sem limite de caractere (ver Onda de correções — campo
# curto demais causava erro ao salvar um dado clínico legítimo mais longo).
class CidadaoBase(BaseModel):
    nome_completo: str = Field(min_length=1)
    nome_social: str | None = None
    cpf: str | None = Field(default=None, max_length=11)
    cns: str | None = Field(default=None, max_length=15)
    data_nascimento: date
    sexo: str = Field(pattern="^[FMI]$")
    nome_mae: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    convenio_id: uuid.UUID | None = None
    numero_carteirinha: str | None = None


class CidadaoCreate(CidadaoBase):
    pass


class CidadaoUpdate(BaseModel):
    nome_completo: str | None = Field(default=None, min_length=1)
    nome_social: str | None = None
    cpf: str | None = Field(default=None, max_length=11)
    cns: str | None = Field(default=None, max_length=15)
    data_nascimento: date | None = None
    sexo: str | None = Field(default=None, pattern="^[FMI]$")
    nome_mae: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    convenio_id: uuid.UUID | None = None
    numero_carteirinha: str | None = None


class ConvenioResumo(ORM):
    id: uuid.UUID
    nome: str
    cnpj: str | None = None


class CidadaoOut(CidadaoBase, ORM):
    id: uuid.UUID
    criado_em: datetime
    idade: int | None = None
    convenio: ConvenioResumo | None = None


# ─────────── Alergias / Medicamentos em uso / Medições ───────────
class AlergiaIn(BaseModel):
    substancia: str
    categoria: str = "MEDICAMENTO"
    gravidade: str = "MODERADA"
    reacao: str | None = None
    ativo: bool = True


class AlergiaOut(AlergiaIn, ORM):
    id: uuid.UUID
    registrado_em: datetime


class MedicamentoUsoIn(BaseModel):
    descricao: str
    posologia: str | None = None
    via: str | None = None
    uso_continuo: bool = True
    inicio: date | None = None
    fim: date | None = None
    ativo: bool = True


class MedicamentoUsoOut(MedicamentoUsoIn, ORM):
    id: uuid.UUID


class MedicaoIn(BaseModel):
    tipo: str
    valor: float
    unidade: str
    aferido_em: datetime | None = None


class MedicaoOut(ORM):
    id: uuid.UUID
    tipo: str
    valor: float
    unidade: str
    aferido_em: datetime


# ─────────── Folha de rosto ───────────
class SerieEvolucao(BaseModel):
    tipo: str
    unidade: str
    pontos: list[dict]  # [{"data": iso, "valor": x}]


class FolhaRostoOut(BaseModel):
    cidadao: CidadaoOut
    alergias: list[AlergiaOut]
    medicamentos_ativos: list[MedicamentoUsoOut]
    consultas_anteriores: list["AtendimentoResumo"]
    evolucao: list[SerieEvolucao]


# ─────────── Atendimento ───────────
class FilaIn(BaseModel):
    cidadao_id: uuid.UUID
    motivo: str | None = None
    tipo: str = "CONSULTA"
    classificacao_risco: str | None = None
    profissional_id: uuid.UUID | None = None  # "quero ser atendido pelo Dr./Dra. X"


class TrocarProfissionalIn(BaseModel):
    profissional_id: uuid.UUID | None = None  # null = tira a preferência (qualquer um atende)


class AcolhimentoIn(BaseModel):
    classificacao_risco: str | None = None
    anotacao: str | None = None
    motivo: str | None = None
    pa_sistolica: float | None = None
    pa_diastolica: float | None = None
    peso: float | None = None
    altura: float | None = None
    temperatura: float | None = None
    freq_cardiaca: float | None = None
    freq_respiratoria: float | None = None
    saturacao: float | None = None
    glicemia: float | None = None


class ProblemaIn(BaseModel):
    # LIVRE = diagnóstico digitado à mão, sem código de CID-10/CIAP-2
    sistema: str = Field(pattern="^(CID10|CIAP2|LIVRE)$")
    codigo: str | None = None
    descricao: str


class ProblemaOut(ProblemaIn, ORM):
    id: uuid.UUID


class SoapIn(BaseModel):
    subjetivo: str | None = None
    objetivo: str | None = None
    avaliacao: str | None = None
    plano: str | None = None
    # sinais vitais estruturados (O) — gravados como Medicao
    pa_sistolica: float | None = None
    pa_diastolica: float | None = None
    peso: float | None = None
    altura: float | None = None
    temperatura: float | None = None
    freq_cardiaca: float | None = None
    freq_respiratoria: float | None = None
    saturacao: float | None = None
    glicemia: float | None = None


class FinalizarIn(BaseModel):
    desfecho: str
    desfecho_obs: str | None = None
    retorno_data: date | None = None
    encaminhamento_tipo: str = "CONSULTA_ESPECIALIZADA"
    encaminhamento_especialidade: str | None = None
    encaminhamento_cid: str | None = None
    encaminhamento_motivo: str | None = None
    encaminhamento_prioridade: str = "ROTINA"


class CidadaoResumo(ORM):
    id: uuid.UUID
    nome_completo: str
    nome_social: str | None = None
    telefone: str | None = None
    email: str | None = None
    data_nascimento: date
    sexo: str
    idade: int | None = None


class AtendimentoResumo(ORM):
    id: uuid.UUID
    status: str
    tipo: str
    motivo: str | None = None
    classificacao_risco: str | None = None
    criado_em: datetime
    inicio_atendimento: datetime | None = None
    fim_atendimento: datetime | None = None
    retorno_data: date | None = None
    desfecho: str | None = None
    assinado: bool = False
    acolhido_em: datetime | None = None
    cidadao: CidadaoResumo | None = None
    profissional: UsuarioResumo | None = None
    unidade: UnidadeResumo | None = None


class PrescricaoIn(BaseModel):
    medicamento: str
    catalogo_id: uuid.UUID | None = None
    posologia: str
    quantidade: str | None = None
    via: str | None = None
    duracao_dias: int | None = None
    uso_continuo: bool = False
    controle_especial: bool = False
    observacao: str | None = None


class PrescricaoOut(PrescricaoIn, ORM):
    id: uuid.UUID


class AtestadoIn(BaseModel):
    tipo: str = "COMPARECIMENTO"
    dias_afastamento: int | None = None
    cid: str | None = None
    data_inicio: date | None = None
    texto: str | None = None  # gerado se vazio


class AtestadoOut(ORM):
    id: uuid.UUID
    tipo: str
    dias_afastamento: int | None = None
    cid: str | None = None
    data_inicio: date | None = None
    texto: str
    emitido_em: datetime


class SolicitacaoExameIn(BaseModel):
    exames: str
    indicacao_clinica: str | None = None
    prioridade: str = "ROTINA"


class SolicitacaoExameOut(SolicitacaoExameIn, ORM):
    id: uuid.UUID
    emitido_em: datetime


class EncaminhamentoOut(ORM):
    id: uuid.UUID
    tipo: str = "CONSULTA_ESPECIALIZADA"
    especialidade: str
    cid: str | None = None
    motivo: str
    prioridade: str


class AtendimentoOut(ORM):
    id: uuid.UUID
    status: str
    tipo: str
    motivo: str | None = None
    classificacao_risco: str | None = None
    acolhimento: str | None = None
    acolhido_em: datetime | None = None
    acolhido_por: UsuarioResumo | None = None
    vitais_acolhimento: dict = {}
    criado_em: datetime
    inicio_atendimento: datetime | None = None
    fim_atendimento: datetime | None = None
    subjetivo: str | None = None
    objetivo: str | None = None
    avaliacao: str | None = None
    plano: str | None = None
    desfecho: str | None = None
    desfecho_obs: str | None = None
    retorno_data: date | None = None
    assinado: bool
    assinado_em: datetime | None = None
    cidadao: CidadaoResumo | None = None
    profissional: UsuarioResumo | None = None
    unidade: UnidadeResumo | None = None
    problemas: list[ProblemaOut] = []
    prescricoes: list[PrescricaoOut] = []
    atestados: list[AtestadoOut] = []
    solicitacoes_exame: list[SolicitacaoExameOut] = []
    encaminhamentos: list[EncaminhamentoOut] = []


# ─────────── Catálogos ───────────
class MedicamentoCatalogoOut(ORM):
    id: uuid.UUID
    nome: str
    principio_ativo: str | None = None
    apresentacao: str | None = None
    posologia_usual: str | None = None
    disponivel_farmacia: bool


class CodigoOut(ORM):
    codigo: str
    descricao: str


class ExameCatalogoOut(ORM):
    id: uuid.UUID
    nome: str
    sinonimia: str | None = None


class PainelOut(BaseModel):
    aguardando: int
    sem_classificacao: int
    em_acolhimento_pendente: int
    em_atendimento: int
    finalizados_hoje: int
    cidadaos: int
    retornos_7dias: int
    agendamentos_hoje: int = 0
    estoque_baixo: int = 0
    faturamento_hoje: float = 0
    producao_hoje: list[dict] = []  # [{profissional, total}]


class ReabrirIn(BaseModel):
    motivo: str = Field(min_length=3)


# ─────────── Relatórios ───────────
class ProducaoOut(BaseModel):
    periodo_de: date
    periodo_ate: date
    total: int
    por_profissional: list[dict]
    por_desfecho: list[dict]
    por_cid: list[dict]
    por_risco: list[dict]


# ─────────── Convênios ───────────
class ConvenioIn(BaseModel):
    nome: str = Field(min_length=1)
    registro_ans: str | None = None
    telefone: str | None = None
    cnpj: str | None = Field(default=None, max_length=14)
    ativo: bool = True


class ConvenioOut(ConvenioIn, ORM):
    id: uuid.UUID
    criado_em: datetime


# ─────────── Agenda ───────────
class AgendamentoIn(BaseModel):
    cidadao_id: uuid.UUID
    profissional_id: uuid.UUID
    data: date
    hora: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duracao_min: int = 30
    tipo: str = "CONSULTA"
    observacao: str | None = None


class AgendamentoOut(ORM):
    id: uuid.UUID
    data: date
    hora: str
    duracao_min: int
    tipo: str
    status: str
    observacao: str | None = None
    atendimento_id: uuid.UUID | None = None
    criado_em: datetime
    cidadao: CidadaoResumo | None = None
    profissional: UsuarioResumo | None = None
    unidade: UnidadeResumo | None = None


# ─────────── Financeiro ───────────
class CobrancaIn(BaseModel):
    cidadao_id: uuid.UUID
    atendimento_id: uuid.UUID | None = None
    descricao: str = Field(min_length=1)
    valor: float = Field(gt=0)
    forma_pagamento: str = "DINHEIRO"
    convenio_id: uuid.UUID | None = None
    codigo_tuss: str | None = None


class CobrancaOut(ORM):
    id: uuid.UUID
    descricao: str
    valor: float
    forma_pagamento: str
    codigo_tuss: str | None = None
    status: str
    criado_em: datetime
    pago_em: datetime | None = None
    atendimento_id: uuid.UUID | None = None
    numero_nf: str | None = None
    nf_emitida_em: datetime | None = None
    cidadao: CidadaoResumo | None = None
    convenio: ConvenioResumo | None = None


class FinanceiroResumoOut(BaseModel):
    periodo_de: date
    periodo_ate: date
    total_faturado: float
    total_pago: float
    total_pendente: float
    por_forma: list[dict]


# ─────────── Estoque ───────────
class ItemEstoqueIn(BaseModel):
    nome: str = Field(min_length=1)
    categoria: str = "MATERIAL"
    unidade: str = "un"
    quantidade_minima: float = 0
    ativo: bool = True


class ItemEstoqueOut(ItemEstoqueIn, ORM):
    id: uuid.UUID
    quantidade: float
    criado_em: datetime


class MovimentoEstoqueIn(BaseModel):
    tipo: str = Field(pattern="^(ENTRADA|SAIDA|AJUSTE)$")
    quantidade: float = Field(gt=0)
    motivo: str | None = None


class MovimentoEstoqueOut(ORM):
    id: uuid.UUID
    tipo: str
    quantidade: float
    motivo: str | None = None
    criado_em: datetime


# ─────────── Portal do paciente ───────────
class PortalLoginIn(BaseModel):
    cpf: str = Field(min_length=1)
    data_nascimento: date


class PortalTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    paciente: CidadaoResumo


class PortalAgendamentoOut(ORM):
    id: uuid.UUID
    data: date
    hora: str
    tipo: str
    status: str
    profissional: UsuarioResumo | None = None


class PortalAtendimentoOut(ORM):
    id: uuid.UUID
    criado_em: datetime
    fim_atendimento: datetime | None = None
    desfecho: str | None = None
    profissional: UsuarioResumo | None = None
    tem_receita: bool = False
    tem_atestado: bool = False
    tem_exames: bool = False


class PortalMeuPainelOut(BaseModel):
    paciente: CidadaoOut
    proximos_agendamentos: list[PortalAgendamentoOut]
    atendimentos_anteriores: list[PortalAtendimentoOut]
