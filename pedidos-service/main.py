from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import crud, schemas, models
from database import SessionLocal, engine, get_db
import redis
import json
import uuid
import requests  # ADICIONE ESTE IMPORT
from typing import List

# Criar tabelas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pedidos Service",
    description="Microsserviço para gerenciamento de pedidos",
    version="1.0.0"
)

# Redis
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# FUNÇÃO PARA INTEGRAÇÃO COM API EXTERNA VIAcep
def validar_e_completar_endereco(cep: str) -> dict:
    """
    Integração com API externa ViaCEP para validar e completar endereço
    """
    try:
        # Remove caracteres não numéricos do CEP
        cep_limpo = ''.join(filter(str.isdigit, cep))
        
        if len(cep_limpo) != 8:
            return {"valido": False, "erro": "CEP deve ter 8 dígitos"}
        
        # Chamada para API externa ViaCEP
        response = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=10)
        
        if response.status_code == 200:
            dados = response.json()
            
            # Verifica se o CEP existe
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

@app.post("/pedidos/", response_model=schemas.Pedido)
def criar_pedido(pedido: schemas.PedidoCreate, db: Session = Depends(get_db)):
    try:
        # VALIDAÇÃO DO CEP COM API EXTERNA VIAcep
        cep = pedido.endereco_entrega.cep
        validacao_cep = validar_e_completar_endereco(cep)
        
        if not validacao_cep["valido"]:
            raise HTTPException(
                status_code=400, 
                detail=f"CEP inválido: {validacao_cep['erro']}"
            )
        
        # Atualiza o endereço com dados da API ViaCEP (opcional)
        endereco_atualizado = pedido.endereco_entrega.dict()
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
        
        # Atualiza o CEP formatado
        endereco_atualizado['cep'] = dados_api['cep']
        
        # Cria o pedido com endereço validado
        pedido_validado = schemas.PedidoCreate(
            cliente_id=pedido.cliente_id,
            restaurante_id=pedido.restaurante_id,
            itens=pedido.itens,
            endereco_entrega=schemas.EnderecoEntrega(**endereco_atualizado)
        )
        
        db_pedido = crud.create_pedido(db=db, pedido=pedido_validado)
        
        # Publicar evento
        evento = {
            "tipo": "PEDIDO_CRIADO",
            "pedido_id": str(db_pedido.id),
            "cliente_id": str(pedido.cliente_id),
            "restaurante_id": str(pedido.restaurante_id),
            "total": float(pedido_validado.total),
            "cep": cep,
            "endereco_validado": True
        }
        redis_client.publish("pedidos", json.dumps(evento))
        
        return db_pedido
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar pedido: {str(e)}"
        )

# Novo endpoint para testar a validação de CEP
@app.get("/cep/validar/{cep}")
def validar_cep(cep: str):
    """
    Endpoint para testar a validação de CEP com a API externa ViaCEP
    """
    resultado = validar_e_completar_endereco(cep)
    return {
        "cep_consultado": cep,
        "api_externa": "ViaCEP",
        "resultado": resultado
    }

@app.get("/pedidos/", response_model=List[schemas.Pedido])
def listar_pedidos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    pedidos = crud.get_all_pedidos(db, skip=skip, limit=limit)
    return pedidos

@app.get("/pedidos/{pedido_id}", response_model=schemas.Pedido)
def obter_pedido(pedido_id: uuid.UUID, db: Session = Depends(get_db)):
    db_pedido = crud.get_pedido(db, pedido_id=pedido_id)
    if db_pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return db_pedido

@app.get("/pedidos/cliente/{cliente_id}", response_model=List[schemas.Pedido])
def listar_pedidos_cliente(cliente_id: uuid.UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    pedidos = crud.get_pedidos_by_cliente(db, cliente_id=cliente_id, skip=skip, limit=limit)
    return pedidos

@app.get("/pedidos/restaurante/{restaurante_id}", response_model=List[schemas.Pedido])
def listar_pedidos_restaurante(restaurante_id: uuid.UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    pedidos = crud.get_pedidos_by_restaurante(db, restaurante_id=restaurante_id, skip=skip, limit=limit)
    return pedidos

@app.put("/pedidos/{pedido_id}/status")
def atualizar_status_pedido(pedido_id: uuid.UUID, status: str, db: Session = Depends(get_db)):
    db_pedido = crud.update_pedido_status(db, pedido_id=pedido_id, status=status)
    if db_pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    # Publicar evento
    evento = {
        "tipo": "PEDIDO_STATUS_ATUALIZADO",
        "pedido_id": str(pedido_id),
        "status": status
    }
    redis_client.publish("pedidos", json.dumps(evento))
    
    return {"message": "Status atualizado com sucesso", "pedido_id": str(pedido_id), "status": status}

@app.delete("/pedidos/{pedido_id}")
def deletar_pedido(pedido_id: uuid.UUID, db: Session = Depends(get_db)):
    db_pedido = crud.delete_pedido(db, pedido_id=pedido_id)
    if db_pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    # Publicar evento
    evento = {
        "tipo": "PEDIDO_DELETED",
        "pedido_id": str(pedido_id)
    }
    redis_client.publish("pedidos", json.dumps(evento))
    
    return {"message": "Pedido deletado com sucesso"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)