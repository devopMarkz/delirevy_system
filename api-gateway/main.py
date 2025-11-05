from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import uuid
from typing import List, Optional

app = FastAPI(
    title="Delivery System API Gateway",
    description="Gateway único para todos os microsserviços do sistema de delivery",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URLs dos serviços
PEDIDOS_SERVICE_URL = os.getenv("PEDIDOS_SERVICE_URL", "http://pedidos-service:8001")
RESTAURANTES_SERVICE_URL = os.getenv("RESTAURANTES_SERVICE_URL", "http://restaurantes-service:8002")
PAGAMENTOS_SERVICE_URL = os.getenv("PAGAMENTOS_SERVICE_URL", "http://pagamentos-service:8003")

@app.get("/")
async def root():
    return {
        "message": "Delivery System API Gateway",
        "services": {
            "pedidos": f"{PEDIDOS_SERVICE_URL}/docs",
            "restaurantes": f"{RESTAURANTES_SERVICE_URL}/docs", 
            "pagamentos": f"{PAGAMENTOS_SERVICE_URL}/docs"
        }
    }

# ========== RESTAURANTES ==========
@app.get("/restaurantes")
async def listar_restaurantes(skip: int = 0, limit: int = 100, ativo: bool = True):
    try:
        response = requests.get(
            f"{RESTAURANTES_SERVICE_URL}/restaurantes/",
            params={"skip": skip, "limit": limit, "ativo": ativo}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar com serviço de restaurantes: {str(e)}")

@app.post("/restaurantes")
async def criar_restaurante(restaurante_data: dict):
    try:
        print(f"🔧 DEBUG: Enviando para restaurantes-service: {restaurante_data}")
        
        # Remove campos None/nulos para evitar problemas
        restaurante_clean = {k: v for k, v in restaurante_data.items() if v is not None}
        
        response = requests.post(
            f"{RESTAURANTES_SERVICE_URL}/restaurantes/", 
            json=restaurante_clean,
            timeout=30
        )
        
        print(f"🔧 DEBUG: Resposta do restaurantes-service: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout ao criar restaurante")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Serviço de restaurantes indisponível")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar restaurante: {str(e)}")

@app.get("/restaurantes/{restaurante_id}")
async def obter_restaurante(restaurante_id: str):
    try:
        response = requests.get(f"{RESTAURANTES_SERVICE_URL}/restaurantes/{restaurante_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter restaurante: {str(e)}")

@app.get("/restaurantes/{restaurante_id}/produtos")
async def listar_produtos_restaurante(restaurante_id: str, skip: int = 0, limit: int = 100):
    try:
        response = requests.get(
            f"{RESTAURANTES_SERVICE_URL}/produtos/restaurante/{restaurante_id}",
            params={"skip": skip, "limit": limit}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar produtos: {str(e)}")

# ========== CATEGORIAS ==========
@app.post("/categorias")
async def criar_categoria(categoria_data: dict):
    try:
        response = requests.post(f"{RESTAURANTES_SERVICE_URL}/categorias/", json=categoria_data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar categoria: {str(e)}")

@app.get("/categorias")
async def listar_categorias(skip: int = 0, limit: int = 100):
    try:
        response = requests.get(
            f"{RESTAURANTES_SERVICE_URL}/categorias/",
            params={"skip": skip, "limit": limit}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar categorias: {str(e)}")

# ========== PRODUTOS ==========
@app.post("/produtos")
async def criar_produto(produto_data: dict):
    try:
        response = requests.post(f"{RESTAURANTES_SERVICE_URL}/produtos/", json=produto_data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar produto: {str(e)}")

# ========== PEDIDOS ==========
@app.post("/pedidos")
async def criar_pedido(pedido_data: dict):
    try:
        response = requests.post(f"{PEDIDOS_SERVICE_URL}/pedidos/", json=pedido_data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar pedido: {str(e)}")

@app.get("/pedidos")
async def listar_pedidos(skip: int = 0, limit: int = 100):
    try:
        response = requests.get(
            f"{PEDIDOS_SERVICE_URL}/pedidos/",
            params={"skip": skip, "limit": limit}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar pedidos: {str(e)}")

@app.get("/pedidos/{pedido_id}")
async def obter_pedido(pedido_id: str):
    try:
        response = requests.get(f"{PEDIDOS_SERVICE_URL}/pedidos/{pedido_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter pedido: {str(e)}")

@app.put("/pedidos/{pedido_id}/status")
async def atualizar_status_pedido(pedido_id: str, status: str):
    try:
        response = requests.put(f"{PEDIDOS_SERVICE_URL}/pedidos/{pedido_id}/status?status={status}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar status: {str(e)}")

# ========== PAGAMENTOS ==========
@app.post("/pagamentos")
async def criar_pagamento(pagamento_data: dict):
    try:
        response = requests.post(f"{PAGAMENTOS_SERVICE_URL}/pagamentos/", json=pagamento_data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar pagamento: {str(e)}")

@app.get("/pagamentos/pedido/{pedido_id}")
async def obter_pagamento_por_pedido(pedido_id: str):
    try:
        response = requests.get(f"{PAGAMENTOS_SERVICE_URL}/pagamentos/pedido/{pedido_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter pagamento: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)