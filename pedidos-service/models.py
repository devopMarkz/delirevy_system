from sqlalchemy import Column, String, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import json
from database import Base

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(UUID(as_uuid=True), nullable=False)
    restaurante_id = Column(UUID(as_uuid=True), nullable=False)
    itens = Column(JSON, nullable=False)  # Lista de itens do pedido
    status = Column(String(50), default="PENDENTE")
    total = Column(Float, nullable=False)
    endereco_entrega = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            'id': str(self.id),
            'cliente_id': str(self.cliente_id),
            'restaurante_id': str(self.restaurante_id),
            'itens': self.itens,
            'status': self.status,
            'total': self.total,
            'endereco_entrega': self.endereco_entrega,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id = Column(UUID(as_uuid=True), ForeignKey('pedidos.id'))
    produto_id = Column(UUID(as_uuid=True), nullable=False)
    produto_nome = Column(String(255), nullable=False)
    quantidade = Column(Float, nullable=False)
    preco_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)