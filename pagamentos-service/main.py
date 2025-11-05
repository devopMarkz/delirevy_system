from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import crud, schemas, models
from database import SessionLocal, engine, get_db
import redis
import json
import uuid
import requests
import os
import threading  # ADICIONE ESTE IMPORT
from typing import List

# Criar tabelas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pagamentos Service",
    description="Microsserviço para processamento de pagamentos",
    version="1.0.0"
)

# Redis
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# LISTENER ASSÍNCRONO PARA EVENTOS DE PEDIDOS
def escutar_eventos_pedidos():
    """Escuta eventos de pedidos para analytics e monitoramento"""
    pubsub = redis_client.pubsub()
    pubsub.subscribe('pedidos')
    
    print("🎧 Pagamentos Service: Iniciando listener de eventos de pedidos...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                evento = json.loads(message['data'])
                
                if evento.get('tipo') == 'PEDIDO_CRIADO':
                    pedido_id = evento['pedido_id']
                    total = evento['total']
                    cliente_id = evento['cliente_id']
                    
                    print(f"💰 ANALYTICS: Novo pedido {pedido_id} criado")
                    print(f"   👤 Cliente: {cliente_id}")
                    print(f"   💰 Valor: R$ {total}")
                    print(f"   📊 Registrado no sistema de analytics de pagamentos")
                    
                    # Em um sistema real, poderia:
                    # - Salvar em banco de analytics
                    # - Pré-processar para fraud detection
                    # - Atualizar métricas em tempo real
                    
                elif evento.get('tipo') == 'PEDIDO_STATUS_ATUALIZADO':
                    pedido_id = evento['pedido_id']
                    status = evento['status']
                    
                    print(f"🔄 STATUS PEDIDO: Pedido {pedido_id} atualizado para: {status}")
                    
                    # Monitorar mudanças de status que podem afetar pagamentos
                    if status in ['CANCELADO', 'ESTORNADO']:
                        print(f"   ⚠️  Atenção: Pedido {pedido_id} cancelado - verificar necessidade de estorno")
                        
            except Exception as e:
                print(f"❌ Erro ao processar evento: {e}")

# INICIAR LISTENER EM THREAD SEPARADA
threading.Thread(target=escutar_eventos_pedidos, daemon=True).start()

# Simulação de gateway de pagamento externo
class PagarmeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pagar.me/1"

    def processar_pagamento(self, pagamento_data: dict):
        # Simulação - em produção, faria HTTP request real
        import random
        transacao_id = f"trans_{uuid.uuid4().hex[:16]}"
        
        # Simular aprovação (90% de sucesso)
        if random.random() < 0.9:
            return {
                "status": "paid",
                "id": transacao_id,
                "authorization_code": f"auth_{uuid.uuid4().hex[:8]}"
            }
        else:
            return {
                "status": "refused",
                "id": transacao_id,
                "refuse_reason": "transaction_declined"
            }

pagarme_client = PagarmeClient(api_key=os.getenv("PAGARME_API_KEY", "ak_test_123456"))

async def processar_pagamento_externo(pagamento: schemas.PagamentoCreate):
    """SEMPRE simula pagamento aprovado - sem API real"""
    # Simulação sempre bem-sucedida para demonstração
    transacao_id = f"trans_{uuid.uuid4().hex[:16]}"
    
    return {
        "status": "paid",  # Sempre aprovado
        "id": transacao_id,
        "authorization_code": f"auth_{uuid.uuid4().hex[:8]}"
    }

async def publicar_evento_pagamento(pagamento_id: uuid.UUID, pedido_id: uuid.UUID, status: str):
    evento = {
        "tipo": "PAGAMENTO_PROCESSADO",
        "pagamento_id": str(pagamento_id),
        "pedido_id": str(pedido_id),
        "status": status
    }
    redis_client.publish("pagamentos", json.dumps(evento))

@app.post("/pagamentos/", response_model=schemas.Pagamento)
async def criar_pagamento(
    pagamento: schemas.PagamentoCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Verificar se já existe pagamento para este pedido
    existing_pagamento = crud.get_pagamento_by_pedido(db, pedido_id=pagamento.pedido_id)
    if existing_pagamento:
        raise HTTPException(status_code=400, detail="Já existe um pagamento para este pedido")
    
    # Criar pagamento no banco
    db_pagamento = crud.create_pagamento(db=db, pagamento=pagamento)
    
    # Processar pagamento em background
    background_tasks.add_task(processar_pagamento_em_background, db_pagamento.id)
    
    return db_pagamento

async def processar_pagamento_em_background(pagamento_id: uuid.UUID):
    """Processa pagamento de forma assíncrona"""
    db = SessionLocal()
    try:
        db_pagamento = crud.get_pagamento(db, pagamento_id=pagamento_id)
        if not db_pagamento:
            return
        
        # Processar com gateway externo
        pagamento_create = schemas.PagamentoCreate(
            pedido_id=db_pagamento.pedido_id,
            cliente_id=db_pagamento.cliente_id,
            valor=db_pagamento.valor,
            metodo_pagamento=db_pagamento.metodo_pagamento,
            dados_pagamento=db_pagamento.dados_pagamento  # Já está desserializado
        )
        
        resultado = await processar_pagamento_externo(pagamento_create)
        
        # Atualizar status do pagamento
        status_map = {"paid": "APROVADO", "refused": "REPROVADO"}
        novo_status = status_map.get(resultado["status"], "REPROVADO")
        
        pagamento_update = schemas.PagamentoUpdate(
            status=novo_status,
            transacao_id=resultado["id"]
        )
        
        db_pagamento_atualizado = crud.update_pagamento(db, pagamento_id=pagamento_id, pagamento_update=pagamento_update)
        
        # Publicar evento
        await publicar_evento_pagamento(pagamento_id, db_pagamento.pedido_id, novo_status)
        
    except Exception as e:
        print(f"Erro ao processar pagamento: {e}")
        # Atualizar status para falha
        pagamento_update = schemas.PagamentoUpdate(status="FALHA")
        crud.update_pagamento(db, pagamento_id=pagamento_id, pagamento_update=pagamento_update)
    finally:
        db.close()

@app.get("/pagamentos/", response_model=List[schemas.Pagamento])
def listar_pagamentos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    pagamentos = crud.get_pagamentos(db, skip=skip, limit=limit)
    return pagamentos

@app.get("/pagamentos/{pagamento_id}", response_model=schemas.Pagamento)
def obter_pagamento(pagamento_id: uuid.UUID, db: Session = Depends(get_db)):
    db_pagamento = crud.get_pagamento(db, pagamento_id=pagamento_id)
    if db_pagamento is None:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return db_pagamento

@app.get("/pagamentos/pedido/{pedido_id}", response_model=schemas.Pagamento)
def obter_pagamento_por_pedido(pedido_id: uuid.UUID, db: Session = Depends(get_db)):
    db_pagamento = crud.get_pagamento_by_pedido(db, pedido_id=pedido_id)
    if db_pagamento is None:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado para este pedido")
    return db_pagamento

@app.put("/pagamentos/{pagamento_id}", response_model=schemas.Pagamento)
def atualizar_pagamento(pagamento_id: uuid.UUID, pagamento_update: schemas.PagamentoUpdate, db: Session = Depends(get_db)):
    db_pagamento = crud.update_pagamento(db, pagamento_id=pagamento_id, pagamento_update=pagamento_update)
    if db_pagamento is None:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return db_pagamento

@app.delete("/pagamentos/{pagamento_id}")
def deletar_pagamento(pagamento_id: uuid.UUID, db: Session = Depends(get_db)):
    db_pagamento = crud.delete_pagamento(db, pagamento_id=pagamento_id)
    if db_pagamento is None:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return {"message": "Pagamento deletado com sucesso"}

# ESTORNOS
@app.post("/estornos/", response_model=schemas.Estorno)
def criar_estorno(estorno: schemas.EstornoCreate, db: Session = Depends(get_db)):
    return crud.create_estorno(db=db, estorno=estorno)

@app.get("/estornos/pagamento/{pagamento_id}", response_model=List[schemas.Estorno])
def listar_estornos_pagamento(pagamento_id: uuid.UUID, db: Session = Depends(get_db)):
    estornos = crud.get_estornos_by_pagamento(db, pagamento_id=pagamento_id)
    return estornos

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)