from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.orm import Session
import crud, schemas, models
from database import SessionLocal, engine, get_db
import redis
import json
import uuid
import requests
import os
import threading
import time
from typing import List
from contextlib import asynccontextmanager
from datetime import datetime # Importar datetime para uso no evento

# Criar tabelas
models.Base.metadata.create_all(bind=engine)

# Redis
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# 🔥 VARIÁVEIS GLOBAIS PARA CONTROLE DO LISTENER
listener_thread = None
listener_stop_event = threading.Event()

# Função para publicar evento
def publicar_evento(channel: str, evento: dict):
    """Publica um evento no canal Redis especificado."""
    try:
        evento['timestamp'] = str(datetime.now())
        redis_client.publish(channel, json.dumps(evento))
        print(f"📢 Evento publicado no canal '{channel}': {evento.get('tipo')}")
    except Exception as e:
        print(f"❌ Erro ao publicar evento no Redis: {e}")

def publicar_evento_pagamento(pagamento_id: uuid.UUID, pedido_id: uuid.UUID, status: str):
    evento = {
        "tipo": "PAGAMENTO_PROCESSADO",
        "pagamento_id": str(pagamento_id),
        "pedido_id": str(pedido_id),
        "status": status
    }
    publicar_evento("pagamentos", evento)

def escutar_eventos_pedidos():
    """Escuta eventos de pedidos para analytics e monitoramento"""
    print("🎧 Pagamentos Service: Iniciando listener de eventos de pedidos...")
    
    while not listener_stop_event.is_set():
        try:
            pubsub = redis_client.pubsub()
            pubsub.subscribe('pedidos')
            
            print("✅ Inscrito no canal 'pedidos'. Aguardando eventos...")
            
            while not listener_stop_event.is_set():
                message = pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
                
                if message:
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
                
                # Pequena pausa para não sobrecarregar a CPU
                time.sleep(0.1)
                        
        except Exception as e:
            if not listener_stop_event.is_set():
                print(f"❌ Erro no listener, reconectando...: {e}")
                time.sleep(2)  # Espera antes de reconectar
    
    print("🛑 Listener de eventos de pedidos parado.")

# 🔥 LIFESPAN MODERNO (substitui o on_event deprecated)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Pagamentos Service: Iniciando servidor...")
    
    # Iniciar o listener do Redis
    listener_stop_event.clear()
    listener_thread = threading.Thread(target=escutar_eventos_pedidos)
    listener_thread.daemon = True
    listener_thread.start()
    print("✅ Listener de eventos de pedidos iniciado automaticamente!")
    
    yield  # Aqui o app está rodando
    
    # Shutdown
    print("🛑 Pagamentos Service: Parando servidor...")
    listener_stop_event.set()
    
    if listener_thread and listener_thread.is_alive():
        listener_thread.join(timeout=5)
        print("✅ Listener de eventos de pedidos parado corretamente.")

# Criar app com lifespan
app = FastAPI(
    title="Pagamentos Service",
    description="Microsserviço para gerenciamento de pagamentos e estornos. Simula a comunicação com um gateway de pagamento externo e publica eventos de 'PAGAMENTO_PROCESSADO'.",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Pagamentos", "description": "Endpoints para gerenciar pagamentos."},
        {"name": "Estornos", "description": "Endpoints para gerenciar estornos."},
        {"name": "Interno", "description": "Endpoints internos ou de saúde do serviço."}
    ]
)

# Simulação de processamento de pagamento em background
def processar_pagamento_em_background(pagamento_id: uuid.UUID):
    """Processa pagamento de forma assíncrona - SEMPRE APROVADO"""
    db = SessionLocal()
    try:
        db_pagamento = crud.get_pagamento(db, pagamento_id=pagamento_id, desserializar_dados=False)
        if not db_pagamento:
            print(f"❌ Pagamento {pagamento_id} não encontrado")
            return
        
        print(f"🔄 Processando pagamento {pagamento_id} em background...")
        
        # 🔥 SIMULAÇÃO SEMPRE APROVADA
        transacao_id = f"trans_{uuid.uuid4().hex[:16]}"
        novo_status = "APROVADO"
        
        pagamento_update = schemas.PagamentoUpdate(
            status=novo_status,
            transacao_id=transacao_id
        )
        
        db_pagamento_atualizado = crud.update_pagamento(db, pagamento_id=pagamento_id, pagamento_update=pagamento_update)
        
        # Publicar evento
        publicar_evento_pagamento(pagamento_id, db_pagamento.pedido_id, novo_status)
        
        print(f"✅ Pagamento {pagamento_id} APROVADO - Transação: {transacao_id}")
        
    except Exception as e:
        print(f"❌ Erro ao processar pagamento: {e}")
        try:
            # Tentar marcar como falha
            pagamento_update = schemas.PagamentoUpdate(status="FALHA", transacao_id=None) 
            crud.update_pagamento(db, pagamento_id=pagamento_id, pagamento_update=pagamento_update)
        except Exception as e_fail:
            db.rollback()
            print(f"❌ Erro ao marcar como FALHA: {e_fail}")
    finally:
        db.close()

@app.get("/", summary="Status do Serviço", tags=["Interno"])
def root():
    """Retorna o status do serviço de pagamentos."""
    return {"message": "Pagamentos Service está online"}

# PAGAMENTOS
@app.post(
    "/pagamentos/", 
    response_model=schemas.Pagamento, 
    summary="Criar Pagamento", 
    tags=["Pagamentos"],
    status_code=status.HTTP_201_CREATED
)
async def criar_pagamento(
    pagamento: schemas.PagamentoCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Cria um novo registro de pagamento e inicia o processamento assíncrono.
    O processamento simula a comunicação com um gateway externo e publica o evento 'PAGAMENTO_PROCESSADO'.
    """
    # Verificar se já existe pagamento para este pedido
    existing_pagamento = crud.get_pagamento_by_pedido_id(db, pedido_id=pagamento.pedido_id)
    if existing_pagamento:
        raise HTTPException(status_code=400, detail="Já existe um pagamento para este pedido")
    
    # Criar pagamento no banco
    db_pagamento = crud.create_pagamento(db=db, pagamento=pagamento)
    
    # Processar pagamento em background
    background_tasks.add_task(processar_pagamento_em_background, db_pagamento.id)
    
    return db_pagamento

@app.get(
    "/pagamentos/", 
    response_model=List[schemas.Pagamento], 
    summary="Listar Pagamentos", 
    tags=["Pagamentos"]
)
def listar_pagamentos(
    skip: int = Query(0, description="Número de itens a pular (offset)"), 
    limit: int = Query(100, description="Número máximo de itens a retornar"), 
    db: Session = Depends(get_db)
):
    """Retorna uma lista de todos os pagamentos cadastrados, com opções de paginação."""
    pagamentos = crud.get_pagamentos(db, skip=skip, limit=limit)
    return pagamentos

@app.get(
    "/pagamentos/{pagamento_id}", 
    response_model=schemas.Pagamento, 
    summary="Obter Pagamento por ID", 
    tags=["Pagamentos"]
)
def obter_pagamento(pagamento_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retorna os detalhes de um pagamento específico pelo seu ID."""
    db_pagamento = crud.get_pagamento(db, pagamento_id=pagamento_id)
    if db_pagamento is None:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return db_pagamento

@app.get(
    "/pagamentos/pedido/{pedido_id}", 
    response_model=schemas.Pagamento, 
    summary="Obter Pagamento por ID do Pedido", 
    tags=["Pagamentos"]
)
def obter_pagamento_por_pedido(pedido_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retorna o pagamento associado a um pedido específico."""
    db_pagamento = crud.get_pagamento_by_pedido_id(db, pedido_id=pedido_id)
    if db_pagamento is None:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado para este pedido")
    return db_pagamento

@app.put(
    "/pagamentos/{pagamento_id}", 
    response_model=schemas.Pagamento, 
    summary="Atualizar Pagamento", 
    tags=["Pagamentos"]
)
def atualizar_pagamento(pagamento_id: uuid.UUID, pagamento_update: schemas.PagamentoUpdate, db: Session = Depends(get_db)):
    """
    Atualiza o status ou informações de transação de um pagamento existente.
    Publica o evento 'PAGAMENTO_PROCESSADO' com o novo status.
    """
    db_pagamento = crud.update_pagamento(db, pagamento_id=pagamento_id, pagamento_update=pagamento_update)
    if db_pagamento is None:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    
    # Publicar evento de pagamento processado com o novo status
    publicar_evento_pagamento(db_pagamento.id, db_pagamento.pedido_id, db_pagamento.status)
    
    return db_pagamento

@app.delete(
    "/pagamentos/{pagamento_id}", 
    summary="Deletar Pagamento", 
    tags=["Pagamentos"],
    status_code=status.HTTP_204_NO_CONTENT
)
def deletar_pagamento(pagamento_id: uuid.UUID, db: Session = Depends(get_db)):
    """Deleta um registro de pagamento do banco de dados. Esta operação é irreversível."""
    db_pagamento = crud.delete_pagamento(db, pagamento_id=pagamento_id)
    if db_pagamento is None:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return {"message": "Pagamento deletado com sucesso"}

# ESTORNOS
@app.post(
    "/estornos/", 
    response_model=schemas.Estorno, 
    summary="Criar Estorno", 
    tags=["Estornos"],
    status_code=status.HTTP_201_CREATED
)
def criar_estorno(estorno: schemas.EstornoCreate, db: Session = Depends(get_db)):
    """
    Cria um novo registro de estorno para um pagamento. 
    Publica o evento 'ESTORNO_PROCESSADO' no Redis.
    """
    db_estorno = crud.create_estorno(db=db, estorno=estorno)
    
    # Publicar evento de estorno (para notificar outros serviços, como o de pedidos)
    evento_estorno = {
        "tipo": "ESTORNO_PROCESSADO",
        "estorno_id": str(db_estorno.id),
        "pagamento_id": str(db_estorno.pagamento_id),
        "valor_estornado": db_estorno.valor_estornado
    }
    publicar_evento("pagamentos", evento_estorno)
    
    return db_estorno

@app.get(
    "/estornos/pagamento/{pagamento_id}", 
    response_model=List[schemas.Estorno], 
    summary="Listar Estornos por Pagamento", 
    tags=["Estornos"]
)
def listar_estornos_pagamento(pagamento_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retorna todos os estornos associados a um pagamento específico."""
    estornos = crud.get_estornos_by_pagamento(db, pagamento_id=pagamento_id)
    return estornos

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
