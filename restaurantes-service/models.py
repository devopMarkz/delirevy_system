from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base

class Restaurante(Base):
    __tablename__ = "restaurantes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text)
    cnpj = Column(String(18), unique=True, nullable=False)
    telefone = Column(String(20))
    email = Column(String(255))
    endereco = Column(Text, nullable=False)
    ativo = Column(Boolean, default=True)
    tempo_medio_entrega = Column(String(50))
    taxa_entrega = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurante_id = Column(UUID(as_uuid=True), ForeignKey('restaurantes.id'))
    categoria_id = Column(UUID(as_uuid=True), ForeignKey('categorias.id'))
    nome = Column(String(255), nullable=False)
    descricao = Column(Text)
    preco = Column(Float, nullable=False)
    disponivel = Column(Boolean, default=True)
    imagem_url = Column(String(500))
    tempo_preparo = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())