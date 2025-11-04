from sqlalchemy.orm import Session
import models
import schemas
import uuid
from typing import List, Optional

def create_pagamento(db: Session, pagamento: schemas.PagamentoCreate):
    db_pagamento = models.Pagamento(**pagamento.dict())
    db.add(db_pagamento)
    db.commit()
    db.refresh(db_pagamento)
    return db_pagamento

def get_pagamento(db: Session, pagamento_id: uuid.UUID):
    return db.query(models.Pagamento).filter(models.Pagamento.id == pagamento_id).first()

def get_pagamento_by_pedido(db: Session, pedido_id: uuid.UUID):
    return db.query(models.Pagamento).filter(models.Pagamento.pedido_id == pedido_id).first()

def get_pagamentos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Pagamento).offset(skip).limit(limit).all()

def update_pagamento(db: Session, pagamento_id: uuid.UUID, pagamento_update: schemas.PagamentoUpdate):
    db_pagamento = db.query(models.Pagamento).filter(models.Pagamento.id == pagamento_id).first()
    if db_pagamento:
        update_data = pagamento_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_pagamento, field, value)
        db.commit()
        db.refresh(db_pagamento)
    return db_pagamento

def delete_pagamento(db: Session, pagamento_id: uuid.UUID):
    db_pagamento = db.query(models.Pagamento).filter(models.Pagamento.id == pagamento_id).first()
    if db_pagamento:
        db.delete(db_pagamento)
        db.commit()
    return db_pagamento

def create_estorno(db: Session, estorno: schemas.EstornoCreate):
    db_estorno = models.Estorno(**estorno.dict())
    db.add(db_estorno)
    db.commit()
    db.refresh(db_estorno)
    return db_estorno

def get_estornos_by_pagamento(db: Session, pagamento_id: uuid.UUID):
    return db.query(models.Estorno).filter(models.Estorno.pagamento_id == pagamento_id).all()