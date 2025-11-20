from pydantic import BaseModel, validator, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import re

# NOVO SCHEMA PARA ITENS SIMPLIFICADOS NO CREATE
class ItemPedidoCreateSimplificado(BaseModel):
    produto_id: uuid.UUID
    quantidade: int

    @field_validator('quantidade')
    @classmethod
    def validar_quantidade(cls, v):
        if v <= 0:
            raise ValueError('Quantidade deve ser maior que zero')
        return v

# SCHEMA ORIGINAL PARA ITENS COMPLETOS (usado na resposta)
class ItemPedidoBase(BaseModel):
    produto_id: uuid.UUID
    produto_nome: str
    quantidade: int
    preco_unitario: float

    @field_validator('quantidade')
    @classmethod
    def validar_quantidade(cls, v):
        if v <= 0:
            raise ValueError('Quantidade deve ser maior que zero')
        return v

    @field_validator('preco_unitario')
    @classmethod
    def validar_preco_unitario(cls, v):
        if v <= 0:
            raise ValueError('Preço unitário deve ser maior que zero')
        return v

    @field_validator('produto_nome')
    @classmethod
    def validar_produto_nome(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Nome do produto não pode estar vazio')
        if len(v) > 255:
            raise ValueError('Nome do produto muito longo')
        return v.strip()

class ItemPedidoCreate(ItemPedidoBase):
    pass

class ItemPedido(ItemPedidoBase):
    id: uuid.UUID
    subtotal: float

    class Config:
        from_attributes = True

class EnderecoEntrega(BaseModel):
    rua: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str
    cep: str

    @field_validator('cep')
    @classmethod
    def validar_formato_cep(cls, v):
        # Remove caracteres não numéricos
        cep_limpo = ''.join(filter(str.isdigit, v))
        
        if len(cep_limpo) != 8:
            raise ValueError('CEP deve conter 8 dígitos')
        
        # Formata o CEP (XXXXX-XXX)
        return f"{cep_limpo[:5]}-{cep_limpo[5:]}"

    @field_validator('estado')
    @classmethod
    def validar_estado(cls, v):
        if len(v) != 2:
            raise ValueError('Estado deve ser a sigla de 2 letras')
        estados_brasileiros = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
            'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
        if v.upper() not in estados_brasileiros:
            raise ValueError('Estado deve ser uma sigla válida do Brasil')
        return v.upper()

    @field_validator('rua', 'bairro', 'cidade')
    @classmethod
    def validar_campo_nao_vazio(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Campo não pode estar vazio')
        return v.strip()

class PedidoBase(BaseModel):
    cliente_id: uuid.UUID
    restaurante_id: uuid.UUID
    itens: List[ItemPedidoCreate]
    endereco_entrega: EnderecoEntrega

    @field_validator('itens')
    @classmethod
    def validar_itens(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Pedido deve conter pelo menos um item')
        return v

class PedidoCreateSimplificado(BaseModel):
    cliente_id: uuid.UUID
    restaurante_id: uuid.UUID
    itens: List[ItemPedidoCreateSimplificado]
    endereco_entrega: EnderecoEntrega

    @field_validator('itens')
    @classmethod
    def validar_itens(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Pedido deve conter pelo menos um item')
        return v

class PedidoCreate(PedidoBase):
    @property
    def total(self):
        return sum(item.quantidade * item.preco_unitario for item in self.itens)

class Pedido(PedidoBase):
    id: uuid.UUID
    status: str
    total: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PedidoUpdate(BaseModel):
    status: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validar_status(cls, v):
        if v is not None:
            status_validos = ["PENDENTE", "CONFIRMADO", "EM_PREPARO", "A_CAMINHO", "ENTREGUE", "CANCELADO"]
            if v not in status_validos:
                raise ValueError(f'Status inválido. Use: {", ".join(status_validos)}')
        return v