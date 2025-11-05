from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base

class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id = Column(UUID(as_uuid=True), nullable=False)
    cliente_id = Column(UUID(as_uuid=True), nullable=False)
    valor = Column(Float, nullable=False)
    metodo_pagamento = Column(String(50), nullable=False)  # cartao, pix, dinheiro
    status = Column(String(50), default="PENDENTE")  # PENDENTE, APROVADO, REPROVADO, ESTORNADO
    transacao_id = Column(String(100))  # ID da transação no gateway
    dados_pagamento = Column(Text)  # JSON com dados sensíveis (criptografado) - MUDEI PARA Text
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Estorno(Base):
    __tablename__ = "estornos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pagamento_id = Column(UUID(as_uuid=True), ForeignKey('pagamentos.id'))
    valor_estornado = Column(Float, nullable=False)
    motivo = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())