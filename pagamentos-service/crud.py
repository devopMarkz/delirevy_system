from sqlalchemy.orm import Session
import models
import schemas
import uuid
import json
from typing import List, Optional

def create_pagamento(db: Session, pagamento: schemas.PagamentoCreate):
    # CONVERTE dict PARA JSON STRING ANTES DE SALVAR
    dados_pagamento_json = None
    if pagamento.dados_pagamento:
        dados_pagamento_json = json.dumps(pagamento.dados_pagamento)
    
    db_pagamento = models.Pagamento(
        pedido_id=pagamento.pedido_id,
        cliente_id=pagamento.cliente_id,
        valor=pagamento.valor,
        metodo_pagamento=pagamento.metodo_pagamento,
        dados_pagamento=dados_pagamento_json,
        status="PENDENTE"
    )
    db.add(db_pagamento)
    db.commit()
    db.refresh(db_pagamento)
    
    # DESSERIALIZA PARA RETORNAR O OBJETO CORRETO
    if db_pagamento.dados_pagamento:
        try:
            db_pagamento.dados_pagamento = json.loads(db_pagamento.dados_pagamento)
        except:
            db_pagamento.dados_pagamento = None
    
    return db_pagamento

def get_pagamento(db: Session, pagamento_id: uuid.UUID):
    pagamento = db.query(models.Pagamento).filter(models.Pagamento.id == pagamento_id).first()
    if pagamento and pagamento.dados_pagamento:
        # CONVERTE JSON STRING DE VOLTA PARA dict
        try:
            pagamento.dados_pagamento = json.loads(pagamento.dados_pagamento)
        except:
            pagamento.dados_pagamento = None
    return pagamento

def get_pagamento_by_pedido(db: Session, pedido_id: uuid.UUID):
    pagamento = db.query(models.Pagamento).filter(models.Pagamento.pedido_id == pedido_id).first()
    if pagamento and pagamento.dados_pagamento:
        # CONVERTE JSON STRING DE VOLTA PARA dict
        try:
            pagamento.dados_pagamento = json.loads(pagamento.dados_pagamento)
        except:
            pagamento.dados_pagamento = None
    return pagamento

def get_pagamentos(db: Session, skip: int = 0, limit: int = 100):
    pagamentos = db.query(models.Pagamento).offset(skip).limit(limit).all()
    # CONVERTE JSON STRING DE VOLTA PARA dict EM TODOS OS PAGAMENTOS
    for pagamento in pagamentos:
        if pagamento.dados_pagamento:
            try:
                pagamento.dados_pagamento = json.loads(pagamento.dados_pagamento)
            except:
                pagamento.dados_pagamento = None
    return pagamentos

def update_pagamento(db: Session, pagamento_id: uuid.UUID, pagamento_update: schemas.PagamentoUpdate):
    db_pagamento = db.query(models.Pagamento).filter(models.Pagamento.id == pagamento_id).first()
    if db_pagamento:
        update_data = pagamento_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_pagamento, field, value)
        db.commit()
        db.refresh(db_pagamento)
        
        # DESSERIALIZA APÓS ATUALIZAR
        if db_pagamento.dados_pagamento:
            try:
                db_pagamento.dados_pagamento = json.loads(db_pagamento.dados_pagamento)
            except:
                db_pagamento.dados_pagamento = None
                
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