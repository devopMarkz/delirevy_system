from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import re  # ADICIONE ESTE IMPORT

class ItemPedidoBase(BaseModel):
    produto_id: uuid.UUID
    produto_nome: str
    quantidade: int
    preco_unitario: float

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

    @validator('cep')
    def validar_formato_cep(cls, v):
        # Remove caracteres não numéricos
        cep_limpo = ''.join(filter(str.isdigit, v))
        
        if len(cep_limpo) != 8:
            raise ValueError('CEP deve conter 8 dígitos')
        
        # Formata o CEP (XXXXX-XXX)
        return f"{cep_limpo[:5]}-{cep_limpo[5:]}"

    @validator('estado')
    def validar_estado(cls, v):
        if len(v) != 2:
            raise ValueError('Estado deve ser a sigla de 2 letras')
        return v.upper()

class PedidoBase(BaseModel):
    cliente_id: uuid.UUID
    restaurante_id: uuid.UUID
    itens: List[ItemPedidoCreate]
    endereco_entrega: EnderecoEntrega

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