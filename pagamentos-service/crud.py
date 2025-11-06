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
    pagamento_retorno = db_pagamento
    if pagamento_retorno.dados_pagamento:
        try:
            pagamento_retorno.dados_pagamento = json.loads(pagamento_retorno.dados_pagamento)
        except:
            pagamento_retorno.dados_pagamento = None
    
    return pagamento_retorno

def get_pagamento(db: Session, pagamento_id: uuid.UUID, desserializar_dados: bool = True):
    pagamento = db.query(models.Pagamento).filter(models.Pagamento.id == pagamento_id).first()
    
    if pagamento and desserializar_dados and pagamento.dados_pagamento:
        # Cria um objeto de retorno para desserializar dados_pagamento
        pagamento_retorno = pagamento
        if pagamento_retorno.dados_pagamento:
            # CONVERTE JSON STRING DE VOLTA PARA dict
            try:
                pagamento_retorno.dados_pagamento = json.loads(pagamento_retorno.dados_pagamento)
            except:
                pagamento_retorno.dados_pagamento = None
        return pagamento_retorno
    
    # Retorna o objeto do banco de dados (com dados_pagamento como string JSON)
    return pagamento

def get_pagamento_by_pedido(db: Session, pedido_id: uuid.UUID, desserializar_dados: bool = True):
    pagamento = db.query(models.Pagamento).filter(models.Pagamento.pedido_id == pedido_id).first()
    
    if pagamento and desserializar_dados and pagamento.dados_pagamento:
        # Cria um objeto de retorno para desserializar dados_pagamento
        pagamento_retorno = pagamento
        if pagamento_retorno.dados_pagamento:
            # CONVERTE JSON STRING DE VOLTA PARA dict
            try:
                pagamento_retorno.dados_pagamento = json.loads(pagamento_retorno.dados_pagamento)
            except:
                pagamento_retorno.dados_pagamento = None
        return pagamento_retorno
    
    # Retorna o objeto do banco de dados (com dados_pagamento como string JSON)
    return pagamento

def get_pagamentos(db: Session, skip: int = 0, limit: int = 100):
    pagamentos = db.query(models.Pagamento).offset(skip).limit(limit).all()
    
    pagamentos_retorno = []
    # CONVERTE JSON STRING DE VOLTA PARA dict EM TODOS OS PAGAMENTOS
    for pagamento in pagamentos:
        pagamento_retorno = pagamento
        if pagamento_retorno.dados_pagamento:
            try:
                pagamento_retorno.dados_pagamento = json.loads(pagamento_retorno.dados_pagamento)
            except:
                pagamento_retorno.dados_pagamento = None
        pagamentos_retorno.append(pagamento_retorno)
        
    return pagamentos_retorno

def update_pagamento(db: Session, pagamento_id: uuid.UUID, pagamento_update: schemas.PagamentoUpdate):
    try:
        db_pagamento = db.query(models.Pagamento).filter(models.Pagamento.id == pagamento_id).first()
        if not db_pagamento:
            return None

        update_data = pagamento_update.dict(exclude_unset=True)

        # Serializa 'dados_pagamento' se presente no update_data
        if 'dados_pagamento' in update_data and isinstance(update_data['dados_pagamento'], dict):
            update_data['dados_pagamento'] = json.dumps(update_data['dados_pagamento'])

        print(f"🔧 Atualizando pagamento {pagamento_id} com dados: {update_data}")

        # Atualiza os campos no objeto do banco de dados
        for key, value in update_data.items():
            setattr(db_pagamento, key, value)

        db.commit()
        db.refresh(db_pagamento)

        # Desserializa 'dados_pagamento' para o retorno
        pagamento_retorno = db_pagamento
        if pagamento_retorno.dados_pagamento and isinstance(pagamento_retorno.dados_pagamento, str):
            try:
                pagamento_retorno.dados_pagamento = json.loads(pagamento_retorno.dados_pagamento)
            except json.JSONDecodeError:
                pass

        print(f"✅ Pagamento {pagamento_id} atualizado para: {db_pagamento.status}")
        return pagamento_retorno

    except Exception as e:
        db.rollback()
        print(f"❌ Erro no update_pagamento: {e}")
        raise

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
