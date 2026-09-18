from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────── Unidades (multiclínica) ───────────────────────────
class Unidade(Base):
    """Onda 5 (Lean Inception) — suporte a mais de uma unidade/filial da clínica."""

    __tablename__ = "unidades"

    id: Mapped[uuid.UUID] = _pk()
    nome: Mapped[str] = mapped_column(Text, unique=True)
    endereco: Mapped[str | None] = mapped_column(Text)
    telefone: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ─────────────────────────── Usuários ───────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = _pk()
    nome: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[str] = mapped_column(String(20))  # ADMIN|MEDICO|ENFERMEIRO|RECEPCAO
    cns: Mapped[str | None] = mapped_column(String(20))
    cbo: Mapped[str | None] = mapped_column(String(20))
    conselho: Mapped[str | None] = mapped_column(Text)  # ex. CRM 12345-ES
    unidade_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("unidades.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    unidade: Mapped["Unidade | None"] = relationship(lazy="joined")


# ─────────────────────────── Convênios ───────────────────────────
class Convenio(Base):
    __tablename__ = "convenios"

    id: Mapped[uuid.UUID] = _pk()
    nome: Mapped[str] = mapped_column(Text, unique=True)
    registro_ans: Mapped[str | None] = mapped_column(String(30))
    telefone: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ─────────────────────────── Cidadão (paciente) ───────────────────────────
class Cidadao(Base):
    __tablename__ = "cidadaos"

    id: Mapped[uuid.UUID] = _pk()
    nome_completo: Mapped[str] = mapped_column(Text)
    nome_social: Mapped[str | None] = mapped_column(Text)
    # CPF e CNS são de tamanho fixo por definição (11 e 15 dígitos) — os
    # únicos limites de caractere que faz sentido manter travados.
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True)
    cns: Mapped[str | None] = mapped_column(String(15), unique=True)
    data_nascimento: Mapped[date] = mapped_column(Date)
    sexo: Mapped[str] = mapped_column(String(1))  # F|M|I
    nome_mae: Mapped[str | None] = mapped_column(Text)
    telefone: Mapped[str | None] = mapped_column(Text)
    endereco: Mapped[str | None] = mapped_column(Text)
    convenio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("convenios.id"))
    numero_carteirinha: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    convenio: Mapped["Convenio | None"] = relationship(lazy="joined")

    @property
    def idade(self) -> int | None:
        if not self.data_nascimento:
            return None
        h = date.today()
        n = self.data_nascimento
        return h.year - n.year - ((h.month, h.day) < (n.month, n.day))

    alergias: Mapped[list["Alergia"]] = relationship(
        back_populates="cidadao", cascade="all, delete-orphan"
    )
    medicamentos: Mapped[list["MedicamentoEmUso"]] = relationship(
        back_populates="cidadao", cascade="all, delete-orphan"
    )
    medicoes: Mapped[list["Medicao"]] = relationship(
        back_populates="cidadao", cascade="all, delete-orphan"
    )
    atendimentos: Mapped[list["Atendimento"]] = relationship(back_populates="cidadao")


class Alergia(Base):
    __tablename__ = "alergias"

    id: Mapped[uuid.UUID] = _pk()
    cidadao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cidadaos.id", ondelete="CASCADE"))
    substancia: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(20), default="MEDICAMENTO")  # MEDICAMENTO|ALIMENTO|AMBIENTAL|OUTRO
    gravidade: Mapped[str] = mapped_column(String(12), default="MODERADA")  # LEVE|MODERADA|GRAVE
    reacao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    cidadao: Mapped["Cidadao"] = relationship(back_populates="alergias")


class MedicamentoEmUso(Base):
    __tablename__ = "medicamentos_em_uso"

    id: Mapped[uuid.UUID] = _pk()
    cidadao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cidadaos.id", ondelete="CASCADE"))
    descricao: Mapped[str] = mapped_column(Text)  # "Losartana 50 mg"
    posologia: Mapped[str | None] = mapped_column(Text)  # "1 comprimido de manhã"
    via: Mapped[str | None] = mapped_column(Text)
    uso_continuo: Mapped[bool] = mapped_column(Boolean, default=True)
    inicio: Mapped[date | None] = mapped_column(Date)
    fim: Mapped[date | None] = mapped_column(Date)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    atendimento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("atendimentos.id", ondelete="SET NULL")
    )

    cidadao: Mapped["Cidadao"] = relationship(back_populates="medicamentos")


class Medicao(Base):
    """Sinais vitais e antropometria — base dos gráficos de evolução."""

    __tablename__ = "medicoes"

    id: Mapped[uuid.UUID] = _pk()
    cidadao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cidadaos.id", ondelete="CASCADE"))
    atendimento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("atendimentos.id", ondelete="SET NULL")
    )
    tipo: Mapped[str] = mapped_column(String(20))
    # PA_SISTOLICA|PA_DIASTOLICA|PESO|ALTURA|IMC|TEMPERATURA|FC|FR|SATO2|GLICEMIA|PERIM_CEFALICO
    valor: Mapped[float] = mapped_column(Float)
    unidade: Mapped[str] = mapped_column(String(12))
    aferido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    cidadao: Mapped["Cidadao"] = relationship(back_populates="medicoes")


# ─────────────────────────── Atendimento ───────────────────────────
class Atendimento(Base):
    __tablename__ = "atendimentos"

    id: Mapped[uuid.UUID] = _pk()
    cidadao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cidadaos.id"))
    profissional_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    unidade_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("unidades.id"))

    status: Mapped[str] = mapped_column(String(16), default="AGUARDANDO")
    # AGUARDANDO | EM_ATENDIMENTO | FINALIZADO | CANCELADO
    tipo: Mapped[str] = mapped_column(String(20), default="CONSULTA")
    motivo: Mapped[str | None] = mapped_column(Text)  # queixa dita no acolhimento
    classificacao_risco: Mapped[str | None] = mapped_column(String(12))  # AZUL|VERDE|AMARELO|LARANJA|VERMELHO

    # acolhimento / pré-consulta da enfermagem
    acolhimento: Mapped[str | None] = mapped_column(Text)
    acolhido_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    acolhido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    inicio_atendimento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fim_atendimento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # SOAP
    subjetivo: Mapped[str | None] = mapped_column(Text)
    objetivo: Mapped[str | None] = mapped_column(Text)
    avaliacao: Mapped[str | None] = mapped_column(Text)
    plano: Mapped[str | None] = mapped_column(Text)

    # desfecho (Passo 5)
    desfecho: Mapped[str | None] = mapped_column(String(24))
    # ALTA | RETORNO_AGENDADO | ENCAMINHAMENTO | OBSERVACAO | ENCAMINHAMENTO_URGENCIA
    desfecho_obs: Mapped[str | None] = mapped_column(Text)
    retorno_data: Mapped[date | None] = mapped_column(Date)
    assinado: Mapped[bool] = mapped_column(Boolean, default=False)
    assinado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cidadao: Mapped["Cidadao"] = relationship(back_populates="atendimentos", lazy="joined")
    profissional: Mapped["Usuario | None"] = relationship(
        foreign_keys=[profissional_id], lazy="joined"
    )
    acolhido_por: Mapped["Usuario | None"] = relationship(
        foreign_keys=[acolhido_por_id], lazy="joined"
    )
    unidade: Mapped["Unidade | None"] = relationship(lazy="joined")
    problemas: Mapped[list["ProblemaAtendimento"]] = relationship(
        back_populates="atendimento", cascade="all, delete-orphan"
    )
    prescricoes: Mapped[list["Prescricao"]] = relationship(
        back_populates="atendimento", cascade="all, delete-orphan"
    )
    atestados: Mapped[list["Atestado"]] = relationship(
        back_populates="atendimento", cascade="all, delete-orphan"
    )
    solicitacoes_exame: Mapped[list["SolicitacaoExame"]] = relationship(
        back_populates="atendimento", cascade="all, delete-orphan"
    )
    encaminhamentos: Mapped[list["Encaminhamento"]] = relationship(
        back_populates="atendimento", cascade="all, delete-orphan"
    )


class ProblemaAtendimento(Base):
    __tablename__ = "atendimento_problemas"

    id: Mapped[uuid.UUID] = _pk()
    atendimento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atendimentos.id", ondelete="CASCADE"))
    sistema: Mapped[str] = mapped_column(String(6))  # CID10 | CIAP2 | LIVRE
    codigo: Mapped[str | None] = mapped_column(String(10))  # vazio quando LIVRE (sem código formal)
    descricao: Mapped[str] = mapped_column(Text)

    atendimento: Mapped["Atendimento"] = relationship(back_populates="problemas")


class Prescricao(Base):
    __tablename__ = "prescricoes"

    id: Mapped[uuid.UUID] = _pk()
    atendimento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atendimentos.id", ondelete="CASCADE"))
    medicamento: Mapped[str] = mapped_column(Text)
    catalogo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalogo_medicamentos.id"))
    posologia: Mapped[str] = mapped_column(Text)
    quantidade: Mapped[str | None] = mapped_column(Text)
    via: Mapped[str | None] = mapped_column(Text)
    duracao_dias: Mapped[int | None] = mapped_column(Integer)
    uso_continuo: Mapped[bool] = mapped_column(Boolean, default=False)
    controle_especial: Mapped[bool] = mapped_column(Boolean, default=False)
    # receituário de controle especial (Portaria SVS/MS 344/98) — psicotrópicos,
    # entorpecentes etc.; imprime em documento separado, com 2 vias
    observacao: Mapped[str | None] = mapped_column(Text)

    atendimento: Mapped["Atendimento"] = relationship(back_populates="prescricoes")


class Atestado(Base):
    __tablename__ = "atestados"

    id: Mapped[uuid.UUID] = _pk()
    atendimento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atendimentos.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(20), default="COMPARECIMENTO")  # COMPARECIMENTO|AFASTAMENTO
    dias_afastamento: Mapped[int | None] = mapped_column(Integer)
    cid: Mapped[str | None] = mapped_column(Text)
    data_inicio: Mapped[date | None] = mapped_column(Date)
    texto: Mapped[str] = mapped_column(Text)
    emitido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    atendimento: Mapped["Atendimento"] = relationship(back_populates="atestados")


class SolicitacaoExame(Base):
    __tablename__ = "solicitacoes_exame"

    id: Mapped[uuid.UUID] = _pk()
    atendimento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atendimentos.id", ondelete="CASCADE"))
    exames: Mapped[str] = mapped_column(Text)  # um por linha
    indicacao_clinica: Mapped[str | None] = mapped_column(Text)
    prioridade: Mapped[str] = mapped_column(String(10), default="ROTINA")  # ROTINA|URGENTE
    emitido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    atendimento: Mapped["Atendimento"] = relationship(back_populates="solicitacoes_exame")


class Encaminhamento(Base):
    __tablename__ = "encaminhamentos"

    id: Mapped[uuid.UUID] = _pk()
    atendimento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atendimentos.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(28), default="CONSULTA_ESPECIALIZADA")
    # CONSULTA_ESPECIALIZADA | AVALIACAO_CIRURGICA | EXAMES_ESPECIALIZADOS | URGENCIA | OUTRO
    especialidade: Mapped[str] = mapped_column(Text)
    # o autocomplete de CID manda "código — descrição" (não só o código), daí
    # ser Text e não um VARCHAR curto — era o campo que estourava (bug relatado)
    cid: Mapped[str | None] = mapped_column(Text)
    motivo: Mapped[str] = mapped_column(Text)
    prioridade: Mapped[str] = mapped_column(String(12), default="ROTINA")

    atendimento: Mapped["Atendimento"] = relationship(back_populates="encaminhamentos")


# ─────────────────────────── Catálogos ───────────────────────────
class CatalogoMedicamento(Base):
    __tablename__ = "catalogo_medicamentos"

    id: Mapped[uuid.UUID] = _pk()
    nome: Mapped[str] = mapped_column(Text)
    principio_ativo: Mapped[str | None] = mapped_column(Text)
    apresentacao: Mapped[str | None] = mapped_column(Text)
    posologia_usual: Mapped[str | None] = mapped_column(Text)  # sugestão exibida ao escolher o medicamento
    disponivel_farmacia: Mapped[bool] = mapped_column(Boolean, default=True)


class CatalogoCID(Base):
    __tablename__ = "catalogo_cid10"
    codigo: Mapped[str] = mapped_column(String(10), primary_key=True)
    descricao: Mapped[str] = mapped_column(Text)


class CatalogoCIAP(Base):
    __tablename__ = "catalogo_ciap2"
    codigo: Mapped[str] = mapped_column(String(10), primary_key=True)
    descricao: Mapped[str] = mapped_column(Text)


class CatalogoExame(Base):
    __tablename__ = "catalogo_exames"
    id: Mapped[uuid.UUID] = _pk()
    nome: Mapped[str] = mapped_column(Text)
    sinonimia: Mapped[str | None] = mapped_column(Text)


# ─────────────────────────── Agenda ───────────────────────────
class Agendamento(Base):
    """Agenda de consultas — marcação prévia, independente da fila do dia (Passo 1)."""

    __tablename__ = "agendamentos"

    id: Mapped[uuid.UUID] = _pk()
    cidadao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cidadaos.id"))
    profissional_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    unidade_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("unidades.id"))
    atendimento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("atendimentos.id", ondelete="SET NULL")
    )

    data: Mapped[date] = mapped_column(Date)
    hora: Mapped[str] = mapped_column(String(5))  # "HH:MM"
    duracao_min: Mapped[int] = mapped_column(Integer, default=30)
    tipo: Mapped[str] = mapped_column(String(30), default="CONSULTA")
    status: Mapped[str] = mapped_column(String(14), default="AGENDADO")
    # AGENDADO | CONFIRMADO | ATENDIDO | FALTOU | CANCELADO
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    cidadao: Mapped["Cidadao"] = relationship(lazy="joined")
    profissional: Mapped["Usuario"] = relationship(foreign_keys=[profissional_id], lazy="joined")
    unidade: Mapped["Unidade | None"] = relationship(lazy="joined")


# ─────────────────────────── Financeiro ───────────────────────────
class Cobranca(Base):
    """Cobrança/recebimento — particular, cartão, PIX ou convênio."""

    __tablename__ = "cobrancas"

    id: Mapped[uuid.UUID] = _pk()
    cidadao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cidadaos.id"))
    atendimento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("atendimentos.id", ondelete="SET NULL")
    )
    convenio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("convenios.id"))
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))

    descricao: Mapped[str] = mapped_column(Text)
    valor: Mapped[float] = mapped_column(Float)
    forma_pagamento: Mapped[str] = mapped_column(String(16), default="DINHEIRO")
    # DINHEIRO | PIX | CARTAO_DEBITO | CARTAO_CREDITO | CONVENIO | BOLETO
    codigo_tuss: Mapped[str | None] = mapped_column(String(20))  # procedimento, p/ guia TISS
    status: Mapped[str] = mapped_column(String(12), default="PENDENTE")  # PENDENTE|PAGO|CANCELADO
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    pago_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cidadao: Mapped["Cidadao"] = relationship(lazy="joined")
    convenio: Mapped["Convenio | None"] = relationship(lazy="joined")
    atendimento: Mapped["Atendimento | None"] = relationship(lazy="joined")


# ─────────────────────────── Estoque ───────────────────────────
class ItemEstoque(Base):
    __tablename__ = "itens_estoque"

    id: Mapped[uuid.UUID] = _pk()
    nome: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(20), default="MATERIAL")  # MEDICAMENTO|MATERIAL|INSUMO
    unidade: Mapped[str] = mapped_column(String(20), default="un")
    quantidade: Mapped[float] = mapped_column(Float, default=0)
    quantidade_minima: Mapped[float] = mapped_column(Float, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MovimentoEstoque(Base):
    __tablename__ = "movimentos_estoque"

    id: Mapped[uuid.UUID] = _pk()
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens_estoque.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(10))  # ENTRADA|SAIDA|AJUSTE
    quantidade: Mapped[float] = mapped_column(Float)
    motivo: Mapped[str | None] = mapped_column(Text)
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    item: Mapped["ItemEstoque"] = relationship()
