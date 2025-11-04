from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

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