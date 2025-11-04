from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import crud, schemas, models
from database import SessionLocal, engine, get_db
import redis
import json
import uuid
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

@app.post("/pedidos/", response_model=schemas.Pedido)
def criar_pedido(pedido: schemas.PedidoCreate, db: Session = Depends(get_db)):
    try:
        db_pedido = crud.create_pedido(db=db, pedido=pedido)
        
        # Publicar evento
        evento = {
            "tipo": "PEDIDO_CRIADO",
            "pedido_id": str(db_pedido.id),
            "cliente_id": str(pedido.cliente_id),
            "restaurante_id": str(pedido.restaurante_id),
            "total": float(pedido.total)
        }
        redis_client.publish("pedidos", json.dumps(evento))
        
        return db_pedido
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar pedido: {str(e)}"
        )

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
        "tipo": "PEDIDO_DELETADO",
        "pedido_id": str(pedido_id)
    }
    redis_client.publish("pedidos", json.dumps(evento))
    
    return {"message": "Pedido deletado com sucesso"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)