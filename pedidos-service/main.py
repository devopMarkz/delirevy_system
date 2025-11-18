from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import crud, schemas, models
from database import SessionLocal, engine, get_db
import redis
import json
import uuid
import requests
import threading
import time
from typing import List
from contextlib import asynccontextmanager
from datetime import datetime
from pydantic import ValidationError
from fastapi.responses import Response

models.Base.metadata.create_all(bind=engine)

listener_thread = None
listener_stop_event = threading.Event()

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

RESTAURANTES_SERVICE_URL = "http://restaurantes-service:8002"

def buscar_produto_no_restaurante_service(produto_id: uuid.UUID):
    try:
        response = requests.get(
            f"{RESTAURANTES_SERVICE_URL}/produtos/{produto_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            error_detail = response.json().get('detail', f'Erro ao buscar produto: {response.status_code}')
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout ao buscar produto no serviço de restaurantes")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Serviço de restaurantes indisponível")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao buscar produto: {str(e)}")

def buscar_restaurante_no_restaurante_service(restaurante_id: uuid.UUID):
    try:
        response = requests.get(
            f"{RESTAURANTES_SERVICE_URL}/restaurantes/{restaurante_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            error_detail = response.json().get('detail', f'Erro ao buscar restaurante: {response.status_code}')
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout ao buscar restaurante no serviço de restaurantes")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Serviço de restaurantes indisponível")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao buscar restaurante: {str(e)}")

# Função para validar se o produto pertence ao restaurante
def validar_produto_pertence_ao_restaurante(produto: dict, restaurante_id: uuid.UUID):
    produto_restaurante_id = produto.get('restaurante_id')
    
    if not produto_restaurante_id:
        raise HTTPException(
            status_code=500,
            detail="Produto não possui restaurante_id associado"
        )
    
    if str(produto_restaurante_id) != str(restaurante_id):
        raise HTTPException(
            status_code=400,
            detail=f"Produto {produto.get('nome', 'Unknown')} não pertence ao restaurante especificado"
        )

# Validar e completar todos os dados do pedido
def validar_e_completar_dados_pedido(pedido_simplificado: schemas.PedidoCreateSimplificado):
    print(f"Validando restaurante: {pedido_simplificado.restaurante_id}")
    
    restaurante = buscar_restaurante_no_restaurante_service(pedido_simplificado.restaurante_id)
    
    if not restaurante:
        raise HTTPException(
            status_code=404,
            detail=f"Restaurante não encontrado: {pedido_simplificado.restaurante_id}"
        )
    
    if not restaurante.get('ativo', True):
        raise HTTPException(
            status_code=400,
            detail=f"Restaurante não está ativo: {restaurante.get('nome', 'Unknown')}"
        )
    
    print(f"Restaurante validado: {restaurante.get('nome', 'Unknown')}")
    
    itens_completos = []
    
    for item_simplificado in pedido_simplificado.itens:
        print(f"Validando produto: {item_simplificado.produto_id}")
        
        produto = buscar_produto_no_restaurante_service(item_simplificado.produto_id)
        
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto não encontrado: {item_simplificado.produto_id}"
            )
        
        if not produto.get('disponivel', True):
            raise HTTPException(
                status_code=400,
                detail=f"Produto não disponível: {produto.get('nome', 'Unknown')}"
            )
        
        validar_produto_pertence_ao_restaurante(produto, pedido_simplificado.restaurante_id)
        
        item_completo = schemas.ItemPedidoCreate(
            produto_id=item_simplificado.produto_id,
            produto_nome=produto['nome'],
            quantidade=item_simplificado.quantidade,
            preco_unitario=produto['preco']
        )
        
        itens_completos.append(item_completo)
        print(f"Produto validado: {produto['nome']} - R$ {produto['preco']}")
    
    return itens_completos, restaurante

def publicar_evento(channel: str, evento: dict):
    try:
        evento['timestamp'] = str(datetime.now())
        redis_client.publish(channel, json.dumps(evento))
        print(f"📢 Evento publicado no canal '{channel}': {evento.get('tipo')}")
    except Exception as e:
        print(f"❌ Erro ao publicar evento no Redis: {e}")

def escutar_eventos_pagamentos():
    """Escuta eventos de pagamentos para atualizar pedidos automaticamente"""
    print("🎧 Pedidos Service: Iniciando listener de eventos de pagamentos...")
    
    while not listener_stop_event.is_set():
        try:
            pubsub = redis_client.pubsub()
            pubsub.subscribe('pagamentos')
            
            print("✅ Inscrito no canal 'pagamentos'. Aguardando eventos...")
            
            while not listener_stop_event.is_set():
                message = pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
                
                if message:
                    try:
                        evento = json.loads(message['data'])
                        
                        if evento.get('tipo') == 'ESTORNO_PROCESSADO':
                            pedido_id = evento['pedido_id']
                            pagamento_id = evento['pagamento_id']
                            motivo = evento.get('motivo', 'Estorno solicitado')
                            
                            print(f"💸 EVENTO ESTORNO RECEBIDO:")
                            print(f"   📦 Pedido: {pedido_id}")
                            print(f"   💰 Pagamento: {pagamento_id}")
                            print(f"   📝 Motivo: {motivo}")
                            
                            # ATUALIZAR STATUS DO PEDIDO PARA CANCELADO
                            db = SessionLocal()
                            try:
                                pedido_atualizado = crud.update_pedido_status(db, uuid.UUID(pedido_id), "CANCELADO")
                                if pedido_atualizado:
                                    print(f"   ❌ Pedido {pedido_id} cancelado devido a estorno")
                                    
                                    # Publicar evento de cancelamento
                                    evento_status = {
                                        "tipo": "PEDIDO_STATUS_ATUALIZADO",
                                        "pedido_id": pedido_id,
                                        "status": "CANCELADO",
                                        "restaurante_id": str(pedido_atualizado.restaurante_id),
                                        "motivo": f"Estorno processado: {motivo}"
                                    }
                                    publicar_evento("pedidos", evento_status)
                                    
                                else:
                                    print(f"   ⚠️  Pedido {pedido_id} não encontrado para cancelamento")
                                    
                            except Exception as e:
                                print(f"   ❌ Erro ao cancelar pedido por estorno: {e}")
                            finally:
                                db.close()
                        
                        elif evento.get('tipo') == 'PAGAMENTO_PROCESSADO':
                            pedido_id = evento['pedido_id']
                            status_pagamento = evento['status']
                            pagamento_id = evento['pagamento_id']
                            
                            print(f"💳 EVENTO PAGAMENTO RECEBIDO:")
                            print(f"   📦 Pedido: {pedido_id}")
                            print(f"   💰 Pagamento: {pagamento_id}")
                            print(f"   📊 Status: {status_pagamento}")
                            
                            # ATUALIZAR STATUS DO PEDIDO AUTOMATICAMENTE
                            db = SessionLocal()
                            try:
                                if status_pagamento == "APROVADO":
                                    pedido_atualizado = crud.update_pedido_status(db, uuid.UUID(pedido_id), "CONFIRMADO")
                                    if pedido_atualizado:
                                        print(f"   ✅ Pedido {pedido_id} confirmado automaticamente!")
                                        
                                        # Publicar evento de status atualizado
                                        evento_status = {
                                            "tipo": "PEDIDO_STATUS_ATUALIZADO",
                                            "pedido_id": pedido_id,
                                            "status": "CONFIRMADO",
                                            "restaurante_id": str(pedido_atualizado.restaurante_id),
                                            "motivo": "Pagamento aprovado automaticamente"
                                        }
                                        publicar_evento("pedidos", evento_status)
                                        print(f"   📢 Evento de confirmação publicado!")
                                        
                                    else:
                                        print(f"   ❌ Pedido {pedido_id} não encontrado!")
                                        
                                elif status_pagamento == "REPROVADO":
                                    pedido_atualizado = crud.update_pedido_status(db, uuid.UUID(pedido_id), "CANCELADO")
                                    if pedido_atualizado:
                                        print(f"   ❌ Pedido {pedido_id} cancelado (pagamento reprovado)")
                                        
                                        # Publicar evento de cancelamento
                                        evento_status = {
                                            "tipo": "PEDIDO_STATUS_ATUALIZADO", 
                                            "pedido_id": pedido_id,
                                            "status": "CANCELADO",
                                            "restaurante_id": str(pedido_atualizado.restaurante_id),
                                            "motivo": "Pagamento reprovado"
                                        }
                                        publicar_evento("pedidos", evento_status)
                                        
                                elif status_pagamento == "FALHA":
                                    print(f"   ⚠️  Falha no processamento do pagamento {pagamento_id}")
                                    
                            except Exception as e:
                                print(f"   ❌ Erro ao atualizar pedido: {e}")
                            finally:
                                db.close()
                                
                    except Exception as e:
                        print(f"❌ Erro ao processar evento de pagamento: {e}")
                
                time.sleep(0.1)
                        
        except Exception as e:
            if not listener_stop_event.is_set():
                print(f"❌ Erro no listener, reconectando...: {e}")
                time.sleep(2)
    
    print("🛑 Listener de eventos de pagamentos parado.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Pedidos Service: Iniciando servidor...")
    
    listener_stop_event.clear()
    listener_thread = threading.Thread(target=escutar_eventos_pagamentos)
    listener_thread.daemon = True
    listener_thread.start()
    print("Listener de eventos de pagamentos iniciado automaticamente!")
    
    yield
    
    print("Pedidos Service: Parando servidor...")
    listener_stop_event.set()
    
    if listener_thread and listener_thread.is_alive():
        listener_thread.join(timeout=5)
        print("Listener de eventos de pagamentos parado corretamente.")

# Criar app com lifespan
app = FastAPI(
    title="Pedidos Service",
    description="Microsserviço para gerenciamento de pedidos. Inclui validação de endereço via ViaCEP e comunicação assíncrona via Redis.",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Pedidos", "description": "Endpoints para gerenciar o ciclo de vida dos pedidos."},
        {"name": "Utilitários", "description": "Endpoints de utilidade, como validação de CEP."},
        {"name": "Interno", "description": "Endpoints internos ou de saúde do serviço."}
    ]
)

def validar_e_completar_endereco(cep: str) -> dict:
    """
    Integração com API externa ViaCEP para validar e completar endereço
    """
    try:
        cep_limpo = ''.join(filter(str.isdigit, cep))
        
        if len(cep_limpo) != 8:
            return {"valido": False, "erro": "CEP deve ter 8 dígitos"}
        
        response = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=10)
        
        if response.status_code == 200:
            dados = response.json()
            
            if 'erro' not in dados:
                return {
                    "valido": True,
                    "dados_endereco": {
                        "cep": dados.get('cep', cep),
                        "logradouro": dados.get('logradouro', ''),
                        "bairro": dados.get('bairro', ''),
                        "cidade": dados.get('localidade', ''),
                        "estado": dados.get('uf', ''),
                        "complemento": dados.get('complemento', '')
                    }
                }
            else:
                return {"valido": False, "erro": "CEP não encontrado"}
        else:
            return {"valido": False, "erro": "Erro na consulta do CEP"}
            
    except requests.exceptions.Timeout:
        return {"valido": False, "erro": "Timeout na consulta do CEP"}
    except requests.exceptions.ConnectionError:
        return {"valido": False, "erro": "Erro de conexão com o serviço de CEP"}
    except Exception as e:
        return {"valido": False, "erro": f"Erro inesperado: {str(e)}"}

@app.get("/", summary="Status do Serviço", tags=["Interno"])
def root():
    return {"message": "Pedidos Service está online"}

# PEDIDOS
@app.post(
    "/pedidos/", 
    summary="Criar Novo Pedido", 
    tags=["Pedidos"],
    status_code=status.HTTP_201_CREATED
)
def criar_pedido(pedido: schemas.PedidoCreateSimplificado, db: Session = Depends(get_db)):
    """
    Cria um novo pedido no sistema. 
    Realiza a validação do endereço de entrega via API externa (ViaCEP).
    Busca automaticamente nome e preço dos produtos no serviço de restaurantes.
    Valida se restaurante existe e se produtos pertencem ao restaurante.
    Após a criação, publica o evento 'PEDIDO_CRIADO' no Redis.
    """
    try:
        if not pedido.itens or len(pedido.itens) == 0:
            raise HTTPException(
                status_code=400,
                detail="Pedido deve conter pelo menos um item"
            )
        
        print(f"🔄 Validando restaurante e {len(pedido.itens)} itens do pedido...")
        itens_completos, restaurante = validar_e_completar_dados_pedido(pedido)
        
        print(f"✅ Todos os dados validados com sucesso!")
        print(f"   🏠 Restaurante: {restaurante.get('nome', 'Unknown')}")
        for item in itens_completos:
            print(f"   🍕 {item.produto_nome} - R$ {item.preco_unitario} x {item.quantidade}")
        
        # VALIDAÇÃO DO CEP COM API EXTERNA VIAcep
        cep = pedido.endereco_entrega.cep
        validacao_cep = validar_e_completar_endereco(cep)
        
        if not validacao_cep["valido"]:
            raise HTTPException(
                status_code=400, 
                detail=f"CEP inválido: {validacao_cep['erro']}"
            )
        
        # Atualiza o endereço com dados da API ViaCEP (opcional)
        endereco_atualizado = pedido.endereco_entrega.model_dump()
        dados_api = validacao_cep["dados_endereco"]
        
        # Mantém os dados fornecidos pelo usuário, mas completa com dados da API se estiverem vazios
        if not endereco_atualizado.get('rua') and dados_api.get('logradouro'):
            endereco_atualizado['rua'] = dados_api['logradouro']
        if not endereco_atualizado.get('bairro') and dados_api.get('bairro'):
            endereco_atualizado['bairro'] = dados_api['bairro']
        if not endereco_atualizado.get('cidade') and dados_api.get('cidade'):
            endereco_atualizado['cidade'] = dados_api['cidade']
        if not endereco_atualizado.get('estado') and dados_api.get('estado'):
            endereco_atualizado['estado'] = dados_api['estado']
        
        endereco_atualizado['cep'] = dados_api['cep']
        
        pedido_completo = schemas.PedidoCreate(
            cliente_id=pedido.cliente_id,
            restaurante_id=pedido.restaurante_id,
            itens=itens_completos,
            endereco_entrega=schemas.EnderecoEntrega(**endereco_atualizado)
        )
        
        db_pedido = crud.create_pedido(db=db, pedido=pedido_completo)
        
        # Publicar evento
        evento = {
            "tipo": "PEDIDO_CRIADO",
            "pedido_id": str(db_pedido.id),
            "cliente_id": str(pedido.cliente_id),
            "restaurante_id": str(pedido.restaurante_id),
            "restaurante_nome": restaurante.get('nome', 'Unknown'),
            "total": float(pedido_completo.total),
            "cep": cep,
            "endereco_validado": True,
        }
        publicar_evento("pedidos", evento)
        
        print(f"📦 Pedido {db_pedido.id} criado e evento publicado!")
        print(f"💰 Total do pedido: R$ {pedido_completo.total:.2f}")
        
        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"Location": f"/pedidos/{db_pedido.id}"}
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao criar pedido: {str(e)}"
        )

@app.get(
    "/pedidos/", 
    response_model=List[schemas.Pedido], 
    summary="Listar Todos os Pedidos", 
    tags=["Pedidos"]
)
def listar_pedidos(
    skip: int = Query(0, ge=0, description="Número de itens a pular (offset)"), 
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de itens a retornar"), 
    db: Session = Depends(get_db)
):
    """Retorna uma lista de todos os pedidos cadastrados no sistema, com opções de paginação."""
    try:
        pedidos = crud.get_all_pedidos(db, skip=skip, limit=limit)
        return pedidos
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar pedidos: {str(e)}"
        )

@app.get(
    "/pedidos/{pedido_id}", 
    response_model=schemas.Pedido, 
    summary="Obter Pedido por ID", 
    tags=["Pedidos"]
)
def obter_pedido(pedido_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retorna os detalhes de um pedido específico pelo seu ID."""
    try:
        db_pedido = crud.get_pedido(db, pedido_id=pedido_id)
        if db_pedido is None:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        return db_pedido
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter pedido: {str(e)}"
        )

@app.get(
    "/pedidos/cliente/{cliente_id}", 
    response_model=List[schemas.Pedido], 
    summary="Listar Pedidos por Cliente", 
    tags=["Pedidos"]
)
def listar_pedidos_cliente(
    cliente_id: uuid.UUID, 
    skip: int = Query(0, ge=0, description="Número de itens a pular (offset)"), 
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de itens a retornar"), 
    db: Session = Depends(get_db)
):
    """Retorna todos os pedidos feitos por um cliente específico."""
    try:
        pedidos = crud.get_pedidos_by_cliente(db, cliente_id=cliente_id, skip=skip, limit=limit)
        return pedidos
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar pedidos do cliente: {str(e)}"
        )

@app.get(
    "/pedidos/restaurante/{restaurante_id}", 
    response_model=List[schemas.Pedido], 
    summary="Listar Pedidos por Restaurante", 
    tags=["Pedidos"]
)
def listar_pedidos_restaurante(
    restaurante_id: uuid.UUID, 
    skip: int = Query(0, ge=0, description="Número de itens a pular (offset)"), 
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de itens a retornar"), 
    db: Session = Depends(get_db)
):
    """Retorna todos os pedidos direcionados a um restaurante específico."""
    try:
        pedidos = crud.get_pedidos_by_restaurante(db, restaurante_id=restaurante_id, skip=skip, limit=limit)
        return pedidos
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar pedidos do restaurante: {str(e)}"
        )

@app.put(
    "/pedidos/{pedido_id}/status", 
    summary="Atualizar Status do Pedido", 
    tags=["Pedidos"],
    status_code=status.HTTP_204_NO_CONTENT
)
def atualizar_status_pedido(
    pedido_id: uuid.UUID, 
    status: str = Query(..., description="Novo status do pedido (CONFIRMADO, EM_PREPARO, A_CAMINHO, ENTREGUE, CANCELADO)"), 
    db: Session = Depends(get_db)
):
    """
    Atualiza o status de um pedido. 
    Publica o evento 'PEDIDO_STATUS_ATUALIZADO' no Redis.
    """
    try:
        # Validação do status
        status_validos = ["PENDENTE", "CONFIRMADO", "EM_PREPARO", "A_CAMINHO", "ENTREGUE", "CANCELADO"]
        if status not in status_validos:
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido. Use: {', '.join(status_validos)}"
            )
        
        db_pedido = crud.update_pedido_status(db, pedido_id=pedido_id, status=status)
        if db_pedido is None:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        
        # Publicar evento
        evento = {
            "tipo": "PEDIDO_STATUS_ATUALIZADO",
            "pedido_id": str(pedido_id),
            "status": status,
            "restaurante_id": str(db_pedido.restaurante_id) if db_pedido else None,
            "motivo": "Atualização manual"
        }
        publicar_evento("pedidos", evento)
        
        print(f"🔄 Status do pedido {pedido_id} atualizado para: {status}")
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar status do pedido: {str(e)}"
        )

@app.delete(
    "/pedidos/{pedido_id}", 
    summary="Deletar Pedido", 
    tags=["Pedidos"],
    status_code=status.HTTP_204_NO_CONTENT
)
def deletar_pedido(pedido_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        db_pedido = crud.delete_pedido(db, pedido_id=pedido_id)
        if db_pedido is None:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        
        # Publicar evento
        evento = {
            "tipo": "PEDIDO_DELETED",
            "pedido_id": str(pedido_id)
        }
        publicar_evento("pedidos", evento)
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao deletar pedido: {str(e)}"
        )

@app.get("/cep/validar/{cep}", summary="Validar CEP", tags=["Utilitários"])
def validar_cep(cep: str):
    """
    Endpoint para testar a validação de CEP com a API externa ViaCEP.
    Retorna os dados de endereço encontrados ou um erro de validação.
    """
    try:
        resultado = validar_e_completar_endereco(cep)
        return {
            "cep_consultado": cep,
            "api_externa": "ViaCEP",
            "resultado": resultado
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao validar CEP: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
