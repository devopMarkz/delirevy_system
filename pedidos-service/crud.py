from sqlalchemy.orm import Session
import models
import schemas
import uuid
import json  # ADICIONE ESTE IMPORT
from typing import List, Optional

def create_pedido(db: Session, pedido: schemas.PedidoCreate):
    # CONVERTE UUIDs PARA STRING ANTES DE SALVAR
    itens_serializados = []
    for item in pedido.itens:
        itens_serializados.append({
            'produto_id': str(item.produto_id),
            'produto_nome': item.produto_nome,
            'quantidade': item.quantidade,
            'preco_unitario': item.preco_unitario
        })
    
    db_pedido = models.Pedido(
        cliente_id=pedido.cliente_id,
        restaurante_id=pedido.restaurante_id,
        itens=itens_serializados,  # USA A LISTA SERIALIZADA
        total=pedido.total,
        endereco_entrega=pedido.endereco_entrega.dict(),
        status="PENDENTE"
    )
    db.add(db_pedido)
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

def get_pedido(db: Session, pedido_id: uuid.UUID):
    return db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()

def get_pedidos_by_cliente(db: Session, cliente_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.Pedido).filter(
        models.Pedido.cliente_id == cliente_id
    ).offset(skip).limit(limit).all()

def get_pedidos_by_restaurante(db: Session, restaurante_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == restaurante_id
    ).offset(skip).limit(limit).all()

def update_pedido_status(db: Session, pedido_id: uuid.UUID, status: str):
    db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if db_pedido:
        db_pedido.status = status
        db.commit()
        db.refresh(db_pedido)
    return db_pedido

def delete_pedido(db: Session, pedido_id: uuid.UUID):
    db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if db_pedido:
        db.delete(db_pedido)
        db.commit()
    return db_pedido

def get_all_pedidos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Pedido).offset(skip).limit(limit).all()