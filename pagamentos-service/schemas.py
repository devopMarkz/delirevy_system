from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class PagamentoBase(BaseModel):
    pedido_id: uuid.UUID
    cliente_id: uuid.UUID
    valor: float
    metodo_pagamento: str
    dados_pagamento: Optional[Dict[str, Any]] = None

class PagamentoCreate(PagamentoBase):
    pass

class PagamentoUpdate(BaseModel):
    status: Optional[str] = None
    transacao_id: Optional[str] = None

class Pagamento(PagamentoBase):
    id: uuid.UUID
    status: str
    transacao_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EstornoBase(BaseModel):
    pagamento_id: uuid.UUID
    valor_estornado: float
    motivo: Optional[str] = None

class EstornoCreate(EstornoBase):
    pass

class Estorno(EstornoBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True