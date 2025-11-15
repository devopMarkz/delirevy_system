from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
from datetime import datetime
import uuid
import re

class RestauranteBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    cnpj: str
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco: str
    tempo_medio_entrega: Optional[str] = None
    taxa_entrega: float = 0.0

    @field_validator('nome')
    @classmethod
    def validar_nome(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Nome do restaurante não pode estar vazio')
        if len(v) > 255:
            raise ValueError('Nome do restaurante muito longo')
        return v.strip()

    @field_validator('cnpj')
    @classmethod
    def validar_cnpj(cls, v):
        # Remove caracteres não numéricos
        cnpj_limpo = ''.join(filter(str.isdigit, v))
        if len(cnpj_limpo) != 14:
            raise ValueError('CNPJ deve conter 14 dígitos')
        return v

    @field_validator('taxa_entrega')
    @classmethod
    def validar_taxa_entrega(cls, v):
        if v < 0:
            raise ValueError('Taxa de entrega não pode ser negativa')
        return v

    @field_validator('telefone')
    @classmethod
    def validar_telefone(cls, v):
        if v is not None:
            # Remove caracteres não numéricos
            telefone_limpo = ''.join(filter(str.isdigit, v))
            if len(telefone_limpo) < 10:
                raise ValueError('Telefone deve conter pelo menos 10 dígitos')
        return v

class RestauranteCreate(RestauranteBase):
    pass

class RestauranteUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco: Optional[str] = None
    tempo_medio_entrega: Optional[str] = None
    taxa_entrega: Optional[float] = None
    ativo: Optional[bool] = None

    @field_validator('taxa_entrega')
    @classmethod
    def validar_taxa_entrega(cls, v):
        if v is not None and v < 0:
            raise ValueError('Taxa de entrega não pode ser negativa')
        return v

class Restaurante(RestauranteBase):
    id: uuid.UUID
    ativo: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CategoriaBase(BaseModel):
    nome: str
    descricao: Optional[str] = None

    @field_validator('nome')
    @classmethod
    def validar_nome(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Nome da categoria não pode estar vazio')
        if len(v) > 100:
            raise ValueError('Nome da categoria muito longo')
        return v.strip()

class CategoriaCreate(CategoriaBase):
    pass

class Categoria(CategoriaBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class ProdutoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco: float
    tempo_preparo: Optional[str] = None
    imagem_url: Optional[str] = None

    @field_validator('nome')
    @classmethod
    def validar_nome(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Nome do produto não pode estar vazio')
        if len(v) > 255:
            raise ValueError('Nome do produto muito longo')
        return v.strip()

    @field_validator('preco')
    @classmethod
    def validar_preco(cls, v):
        if v <= 0:
            raise ValueError('Preço do produto deve ser maior que zero')
        return v

class ProdutoCreate(ProdutoBase):
    restaurante_id: uuid.UUID
    categoria_id: uuid.UUID

class ProdutoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco: Optional[float] = None
    disponivel: Optional[bool] = None
    tempo_preparo: Optional[str] = None
    imagem_url: Optional[str] = None

    @field_validator('preco')
    @classmethod
    def validar_preco(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Preço do produto deve ser maior que zero')
        return v

class Produto(ProdutoBase):
    id: uuid.UUID
    restaurante_id: uuid.UUID
    categoria_id: uuid.UUID
    disponivel: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RestauranteComProdutos(Restaurante):
    produtos: List[Produto] = []