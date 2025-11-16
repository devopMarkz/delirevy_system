from fastapi import FastAPI, HTTPException, Response, status
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

# Função auxiliar para fazer requisições com tratamento correto de erros
def make_service_request(method: str, url: str, **kwargs):
    """
    Faz requisição para serviços e propaga corretamente os status codes
    """
    try:
        response = requests.request(method, url, **kwargs)
        
        # Se for sucesso (2xx), retorna a resposta completa
        if 200 <= response.status_code < 300:
            return response
        
        # Propaga erros específicos do serviço
        if response.status_code == 400:
            raise HTTPException(status_code=400, detail=response.json().get('detail', 'Bad Request'))
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=response.json().get('detail', 'Not Found'))
        elif response.status_code == 422:
            raise HTTPException(status_code=422, detail=response.json().get('detail', 'Validation Error'))
        else:
            # Para outros códigos de erro, propaga com a mensagem original
            error_detail = response.json().get('detail', f'Service error: {response.status_code}')
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Service timeout")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal gateway error: {str(e)}")

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
    response = make_service_request(
        "GET",
        f"{RESTAURANTES_SERVICE_URL}/restaurantes/",
        params={"skip": skip, "limit": limit, "ativo": ativo}
    )
    return response.json()

@app.post("/restaurantes", status_code=status.HTTP_201_CREATED)
async def criar_restaurante(restaurante_data: dict):
    restaurante_clean = {k: v for k, v in restaurante_data.items() if v is not None}
    
    response = make_service_request(
        "POST",
        f"{RESTAURANTES_SERVICE_URL}/restaurantes/", 
        json=restaurante_clean,
        timeout=30
    )
    
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": response.headers.get("Location", "")}
    )

@app.get("/restaurantes/{restaurante_id}")
async def obter_restaurante(restaurante_id: str):
    response = make_service_request(
        "GET", 
        f"{RESTAURANTES_SERVICE_URL}/restaurantes/{restaurante_id}"
    )
    return response.json()

@app.put("/restaurantes/{restaurante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def atualizar_restaurante(restaurante_id: str, restaurante_data: dict):
    restaurante_clean = {k: v for k, v in restaurante_data.items() if v is not None}
    
    response = make_service_request(
        "PUT",
        f"{RESTAURANTES_SERVICE_URL}/restaurantes/{restaurante_id}", 
        json=restaurante_clean
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.delete("/restaurantes/{restaurante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_restaurante(restaurante_id: str):
    response = make_service_request(
        "DELETE", 
        f"{RESTAURANTES_SERVICE_URL}/restaurantes/{restaurante_id}"
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/restaurantes/{restaurante_id}/produtos")
async def listar_produtos_restaurante(restaurante_id: str, skip: int = 0, limit: int = 100):
    response = make_service_request(
        "GET",
        f"{RESTAURANTES_SERVICE_URL}/produtos/restaurante/{restaurante_id}",
        params={"skip": skip, "limit": limit}
    )
    return response.json()

# ========== CATEGORIAS ==========
@app.post("/categorias", status_code=status.HTTP_201_CREATED)
async def criar_categoria(categoria_data: dict):
    response = make_service_request(
        "POST", 
        f"{RESTAURANTES_SERVICE_URL}/categorias/", 
        json=categoria_data
    )
    
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": response.headers.get("Location", "")}
    )

@app.get("/categorias")
async def listar_categorias(skip: int = 0, limit: int = 100):
    response = make_service_request(
        "GET",
        f"{RESTAURANTES_SERVICE_URL}/categorias/",
        params={"skip": skip, "limit": limit}
    )
    return response.json()

# ========== PRODUTOS ==========
@app.post("/produtos", status_code=status.HTTP_201_CREATED)
async def criar_produto(produto_data: dict):
    response = make_service_request(
        "POST", 
        f"{RESTAURANTES_SERVICE_URL}/produtos/", 
        json=produto_data
    )
    
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": response.headers.get("Location", "")}
    )

@app.get("/produtos/{produto_id}")
async def obter_produto(produto_id: str):
    response = make_service_request(
        "GET", 
        f"{RESTAURANTES_SERVICE_URL}/produtos/{produto_id}"
    )
    return response.json()

@app.put("/produtos/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def atualizar_produto(produto_id: str, produto_data: dict):
    produto_clean = {k: v for k, v in produto_data.items() if v is not None}
    
    response = make_service_request(
        "PUT",
        f"{RESTAURANTES_SERVICE_URL}/produtos/{produto_id}", 
        json=produto_clean
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.delete("/produtos/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_produto(produto_id: str):
    response = make_service_request(
        "DELETE", 
        f"{RESTAURANTES_SERVICE_URL}/produtos/{produto_id}"
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ========== PEDIDOS ==========
@app.post("/pedidos", status_code=status.HTTP_201_CREATED)
async def criar_pedido(pedido_data: dict):
    response = make_service_request(
        "POST", 
        f"{PEDIDOS_SERVICE_URL}/pedidos/", 
        json=pedido_data
    )
    
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": response.headers.get("Location", "")}
    )

@app.get("/pedidos")
async def listar_pedidos(skip: int = 0, limit: int = 100):
    response = make_service_request(
        "GET",
        f"{PEDIDOS_SERVICE_URL}/pedidos/",
        params={"skip": skip, "limit": limit}
    )
    return response.json()

@app.get("/pedidos/{pedido_id}")
async def obter_pedido(pedido_id: str):
    response = make_service_request(
        "GET", 
        f"{PEDIDOS_SERVICE_URL}/pedidos/{pedido_id}"
    )
    return response.json()

@app.put("/pedidos/{pedido_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def atualizar_status_pedido(pedido_id: str, status: str):
    response = make_service_request(
        "PUT", 
        f"{PEDIDOS_SERVICE_URL}/pedidos/{pedido_id}/status?status={status}"
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.delete("/pedidos/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_pedido(pedido_id: str):
    response = make_service_request(
        "DELETE", 
        f"{PEDIDOS_SERVICE_URL}/pedidos/{pedido_id}"
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/pedidos/cliente/{cliente_id}")
async def listar_pedidos_cliente(cliente_id: str, skip: int = 0, limit: int = 100):
    response = make_service_request(
        "GET",
        f"{PEDIDOS_SERVICE_URL}/pedidos/cliente/{cliente_id}",
        params={"skip": skip, "limit": limit}
    )
    return response.json()

@app.get("/pedidos/restaurante/{restaurante_id}")
async def listar_pedidos_restaurante(restaurante_id: str, skip: int = 0, limit: int = 100):
    response = make_service_request(
        "GET",
        f"{PEDIDOS_SERVICE_URL}/pedidos/restaurante/{restaurante_id}",
        params={"skip": skip, "limit": limit}
    )
    return response.json()

# ========== PAGAMENTOS ==========
@app.get("/pagamentos")
async def listar_pagamentos(skip: int = 0, limit: int = 100):
    response = make_service_request(
        "GET",
        f"{PAGAMENTOS_SERVICE_URL}/pagamentos/",
        params={"skip": skip, "limit": limit}
    )
    return response.json()

@app.post("/pagamentos", status_code=status.HTTP_201_CREATED)
async def criar_pagamento(pagamento_data: dict):
    response = make_service_request(
        "POST", 
        f"{PAGAMENTOS_SERVICE_URL}/pagamentos/", 
        json=pagamento_data
    )
    
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": response.headers.get("Location", "")}
    )

@app.get("/pagamentos/{pagamento_id}")
async def obter_pagamento(pagamento_id: str):
    response = make_service_request(
        "GET", 
        f"{PAGAMENTOS_SERVICE_URL}/pagamentos/{pagamento_id}"
    )
    return response.json()

@app.put("/pagamentos/{pagamento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def atualizar_pagamento(pagamento_id: str, pagamento_update: dict):
    response = make_service_request(
        "PUT",
        f"{PAGAMENTOS_SERVICE_URL}/pagamentos/{pagamento_id}", 
        json=pagamento_update
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.delete("/pagamentos/{pagamento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_pagamento(pagamento_id: str):
    response = make_service_request(
        "DELETE", 
        f"{PAGAMENTOS_SERVICE_URL}/pagamentos/{pagamento_id}"
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/pagamentos/pedido/{pedido_id}")
async def obter_pagamento_por_pedido(pedido_id: str):
    response = make_service_request(
        "GET", 
        f"{PAGAMENTOS_SERVICE_URL}/pagamentos/pedido/{pedido_id}"
    )
    return response.json()

# ========== ESTORNOS ==========
@app.post("/estornos", status_code=status.HTTP_201_CREATED)
async def criar_estorno(estorno_data: dict):
    response = make_service_request(
        "POST", 
        f"{PAGAMENTOS_SERVICE_URL}/estornos/", 
        json=estorno_data
    )
    
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": response.headers.get("Location", "")}
    )

@app.get("/estornos/pagamento/{pagamento_id}")
async def listar_estornos_pagamento(pagamento_id: str):
    response = make_service_request(
        "GET", 
        f"{PAGAMENTOS_SERVICE_URL}/estornos/pagamento/{pagamento_id}"
    )
    return response.json()

# ========== UTILITÁRIOS ==========
@app.get("/cep/validar/{cep}")
async def validar_cep(cep: str):
    response = make_service_request(
        "GET", 
        f"{PEDIDOS_SERVICE_URL}/cep/validar/{cep}"
    )
    return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)