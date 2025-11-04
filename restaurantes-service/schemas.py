from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import uuid

class RestauranteBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    cnpj: str
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco: str
    tempo_medio_entrega: Optional[str] = None
    taxa_entrega: float = 0.0

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