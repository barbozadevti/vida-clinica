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


class UsuarioBase(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    email: str
    perfil: str
    cns: str | None = None
    cbo: str | None = None
    conselho: str | None = None
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
    ativo: bool | None = None
    senha: str | None = Field(default=None, min_length=4, max_length=72)


class UsuarioOut(UsuarioBase, ORM):
    id: uuid.UUID
    criado_em: datetime


# ─────────── Cidadão ───────────
class CidadaoBase(BaseModel):
    nome_completo: str = Field(min_length=1, max_length=150)
    nome_social: str | None = None
    cpf: str | None = None
    cns: str | None = None
    data_nascimento: date
    sexo: str = Field(pattern="^[FMI]$")
    nome_mae: str | None = None
    telefone: str | None = None
    endereco: str | None = None


class CidadaoCreate(CidadaoBase):
    pass


class CidadaoUpdate(BaseModel):
    nome_completo: str | None = None
    nome_social: str | None = None
    cpf: str | None = None
    cns: str | None = None
    data_nascimento: date | None = None
    sexo: str | None = Field(default=None, pattern="^[FMI]$")
    nome_mae: str | None = None
    telefone: str | None = None
    endereco: str | None = None


class CidadaoOut(CidadaoBase, ORM):
    id: uuid.UUID
    criado_em: datetime
    idade: int | None = None


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
    sistema: str = Field(pattern="^(CID10|CIAP2)$")
    codigo: str
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
    encaminhamento_especialidade: str | None = None
    encaminhamento_motivo: str | None = None
    encaminhamento_prioridade: str = "ROTINA"


class CidadaoResumo(ORM):
    id: uuid.UUID
    nome_completo: str
    nome_social: str | None = None
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


class PrescricaoIn(BaseModel):
    medicamento: str
    catalogo_id: uuid.UUID | None = None
    posologia: str
    quantidade: str | None = None
    via: str | None = None
    duracao_dias: int | None = None
    uso_continuo: bool = False
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
    especialidade: str
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
