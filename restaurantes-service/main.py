from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import crud, schemas, models
from database import SessionLocal, engine, get_db
import uuid
import redis
import json
import threading
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import List

# Criar tabelas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Restaurantes Service",
    description="Microsserviço para gerenciamento de restaurantes, categorias e produtos. Responsável por notificar restaurantes sobre novos pedidos via e-mail.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Restaurantes", "description": "Endpoints para gerenciar restaurantes."},
        {"name": "Categorias", "description": "Endpoints para gerenciar categorias de produtos."},
        {"name": "Produtos", "description": "Endpoints para gerenciar produtos de restaurantes."},
        {"name": "Interno", "description": "Endpoints internos ou de saúde do serviço."}
    ]
)

# Redis
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# Configurações do SendGrid
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', 'xxx')
EMAIL_REMETENTE = os.getenv('EMAIL_USERNAME', 'marcosacs.2022@gmail.com')

# Função para enviar email
def enviar_email_restaurante(destinatario: str, assunto: str, corpo_html: str):
    """Envia email usando SendGrid"""
    try:
        message = Mail(
            from_email=EMAIL_REMETENTE,
            to_emails=destinatario,
            subject=assunto,
            html_content=corpo_html
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"📧 Email enviado para {destinatario} - Status: {response.status_code}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False

# Função para obter email do restaurante DO BANCO DE DADOS
def obter_email_restaurante(restaurante_id: str) -> str:
    """Obtém o email do restaurante do banco de dados"""
    db = SessionLocal()
    try:
        restaurante = db.query(models.Restaurante).filter(models.Restaurante.id == uuid.UUID(restaurante_id)).first()
        if restaurante and restaurante.email:
            return restaurante.email
        else:
            print(f"⚠️  Restaurante {restaurante_id} não encontrado ou sem email cadastrado")
            return "marcosacs.2022@gmail.com"  # Fallback
    except Exception as e:
        print(f"❌ Erro ao buscar restaurante no banco: {e}")
        return "marcosacs.2022@gmail.com"  # Fallback
    finally:
        db.close()

# Função para obter nome do restaurante DO BANCO DE DADOS
def obter_nome_restaurante(restaurante_id: str) -> str:
    """Obtém o nome do restaurante do banco de dados"""
    db = SessionLocal()
    try:
        restaurante = db.query(models.Restaurante).filter(models.Restaurante.id == uuid.UUID(restaurante_id)).first()
        if restaurante:
            return restaurante.nome
        else:
            return "Restaurante"
    except Exception as e:
        print(f"❌ Erro ao buscar nome do restaurante: {e}")
        return "Restaurante"
    finally:
        db.close()

# LISTENER ASSÍNCRONO PARA EVENTOS DE PEDIDOS
def escutar_eventos_pedidos():
    """Escuta eventos de pedidos para notificar restaurantes"""
    pubsub = redis_client.pubsub()
    pubsub.subscribe('pedidos')
    
    print("🎧 Restaurantes Service: Iniciando listener de eventos de pedidos...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                evento = json.loads(message['data'])
                
                if evento.get('tipo') == 'PEDIDO_CRIADO':
                    restaurante_id = evento['restaurante_id']
                    pedido_id = evento['pedido_id']
                    total = evento['total']
                    cliente_id = evento['cliente_id']
                    
                    # BUSCAR INFORMAÇÕES DO RESTAURANTE NO BANCO
                    email_restaurante = obter_email_restaurante(restaurante_id)
                    nome_restaurante = obter_nome_restaurante(restaurante_id)
                    
                    print(f"🏪 🆕 NOVO PEDIDO RECEBIDO!")
                    print(f"   📋 Pedido ID: {pedido_id}")
                    print(f"   🏠 Restaurante: {nome_restaurante} ({restaurante_id})")
                    print(f"   📧 Email: {email_restaurante}")
                    print(f"   👤 Cliente: {cliente_id}")
                    print(f"   💰 Valor Total: R$ {total:.2f}")
                    
                    # ENVIAR EMAIL PARA O RESTAURANTE
                    assunto = f"🍕 Novo Pedido Recebido - #{pedido_id[:8]}"
                    corpo_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            body {{ font-family: Arial, sans-serif; }}
                            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                            .header {{ background: #ff6b35; color: white; padding: 20px; text-align: center; }}
                            .content {{ padding: 20px; background: #f9f9f9; }}
                            .footer {{ text-align: center; padding: 20px; color: #666; }}
                            .pedido-info {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                            .restaurante-nome {{ font-size: 18px; font-weight: bold; color: #ff6b35; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>🍕 Novo Pedido Recebido!</h1>
                                <p class="restaurante-nome">{nome_restaurante}</p>
                            </div>
                            <div class="content">
                                <h2>Detalhes do Pedido</h2>
                                <div class="pedido-info">
                                    <p><strong>Número do Pedido:</strong> {pedido_id}</p>
                                    <p><strong>Restaurante:</strong> {nome_restaurante}</p>
                                    <p><strong>Cliente ID:</strong> {cliente_id}</p>
                                    <p><strong>Valor Total:</strong> R$ {total:.2f}</p>
                                    <p><strong>Status:</strong> Aguardando confirmação</p>
                                    <p><strong>Data/Hora:</strong> {json.loads(message['data']).get('timestamp', 'Agora')}</p>
                                </div>
                                <p><strong>⚠️ ATENÇÃO:</strong> Prepare o pedido o mais rápido possível!</p>
                                <p>Acesse o sistema para mais detalhes e para confirmar o pedido.</p>
                            </div>
                            <div class="footer">
                                <p>Delivery System - Seu sistema de delivery profissional</p>
                                <p>Este é um email automático, não responda.</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # Enviar email
                    email_enviado = enviar_email_restaurante(email_restaurante, assunto, corpo_html)
                    
                    if email_enviado:
                        print(f"   📧 Email de notificação enviado para: {email_restaurante}")
                        print(f"   🔔 Notificação enviada para o restaurante {nome_restaurante}!")
                    else:
                        print(f"   ⚠️  Falha ao enviar email para: {email_restaurante}")
                    
                elif evento.get('tipo') == 'PEDIDO_STATUS_ATUALIZADO':
                    pedido_id = evento['pedido_id']
                    status = evento['status']
                    restaurante_id = evento.get('restaurante_id')
                    
                    print(f"🔄 ATUALIZAÇÃO DE PEDIDO: {pedido_id}")
                    print(f"   📊 Novo Status: {status}")
                    
                    # Enviar email para atualizações importantes
                    if status == 'CONFIRMADO' and restaurante_id:
                        print(f"   ✅ Pedido confirmado - preparar para produção!")
                        
                        # BUSCAR INFORMAÇÕES DO RESTAURANTE NO BANCO
                        email_restaurante = obter_email_restaurante(restaurante_id)
                        nome_restaurante = obter_nome_restaurante(restaurante_id)
                        
                        # Email de confirmação
                        assunto = f"✅ Pedido Confirmado - #{pedido_id[:8]}"
                        corpo_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <body>
                            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                                <div style="background: #28a745; color: white; padding: 20px; text-align: center;">
                                    <h1>✅ Pedido Confirmado!</h1>
                                    <p style="font-size: 18px; font-weight: bold;">{nome_restaurante}</p>
                                </div>
                                <div style="padding: 20px; background: #f9f9f9;">
                                    <h2>Pedido Pronto para Produção</h2>
                                    <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 5px;">
                                        <p><strong>Número do Pedido:</strong> {pedido_id}</p>
                                        <p><strong>Restaurante:</strong> {nome_restaurante}</p>
                                        <p><strong>Status:</strong> CONFIRMADO</p>
                                    </div>
                                    <p><strong>🚀 INICIAR PREPARO:</strong> O pedido foi confirmado e está pronto para produção.</p>
                                    <p>Inicie o preparo imediatamente para garantir a satisfação do cliente.</p>
                                </div>
                                <div style="text-align: center; padding: 20px; color: #666;">
                                    <p>Delivery System - Sistema Automático de Notificações</p>
                                </div>
                            </div>
                        </body>
                        </html>
                        """
                        enviar_email_restaurante(email_restaurante, assunto, corpo_html)
                        print(f"   📧 Email de confirmação enviado para: {nome_restaurante}")
                        
                    elif status == 'EM_PREPARO':
                        print(f"   👨‍🍳 Pedido em preparo - cozinha notificada!")
                    elif status == 'A_CAMINHO':
                        print(f"   🛵 Pedido a caminho - aguardar entregador!")
                    elif status == 'ENTREGUE':
                        print(f"   🎉 Pedido entregue - finalizado com sucesso!")
                    elif status in ['CANCELADO', 'ESTORNADO']:
                        print(f"   ❌ Pedido cancelado - verificar motivo!")
                        
            except Exception as e:
                print(f"❌ Erro ao processar evento: {e}")

# INICIAR LISTENER EM THREAD SEPARADA
threading.Thread(target=escutar_eventos_pedidos, daemon=True).start()

@app.get("/", summary="Status do Serviço", tags=["Interno"])
def root():
    """Retorna o status do serviço de restaurantes."""
    return {"message": "Restaurantes Service está online"}

# RESTAURANTES
@app.post(
    "/restaurantes/", 
    response_model=schemas.Restaurante, 
    summary="Criar Restaurante", 
    tags=["Restaurantes"],
    status_code=status.HTTP_201_CREATED
)
def criar_restaurante(restaurante: schemas.RestauranteCreate, db: Session = Depends(get_db)):
    """Cria um novo restaurante no banco de dados. Requer um CNPJ único."""
    db_restaurante = crud.get_restaurante_by_cnpj(db, cnpj=restaurante.cnpj)
    if db_restaurante:
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    return crud.create_restaurante(db=db, restaurante=restaurante)

@app.get(
    "/restaurantes/", 
    response_model=List[schemas.Restaurante], 
    summary="Listar Restaurantes", 
    tags=["Restaurantes"]
)
def listar_restaurantes(
    skip: int = Query(0, description="Número de itens a pular (offset)"), 
    limit: int = Query(100, description="Número máximo de itens a retornar"), 
    ativo: bool = Query(True, description="Filtrar por restaurantes ativos"), 
    db: Session = Depends(get_db)
):
    """Retorna uma lista de todos os restaurantes cadastrados, com opções de paginação e filtro por status de atividade."""
    restaurantes = crud.get_restaurantes(db, skip=skip, limit=limit, ativo=ativo)
    return restaurantes

@app.get(
    "/restaurantes/{restaurante_id}", 
    response_model=schemas.Restaurante, 
    summary="Obter Restaurante por ID", 
    tags=["Restaurantes"]
)
def obter_restaurante(restaurante_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retorna os detalhes de um restaurante específico pelo seu ID."""
    db_restaurante = crud.get_restaurante(db, restaurante_id=restaurante_id)
    if db_restaurante is None:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    return db_restaurante

@app.put(
    "/restaurantes/{restaurante_id}", 
    response_model=schemas.Restaurante, 
    summary="Atualizar Restaurante", 
    tags=["Restaurantes"]
)
def atualizar_restaurante(restaurante_id: uuid.UUID, restaurante_update: schemas.RestauranteUpdate, db: Session = Depends(get_db)):
    """Atualiza as informações de um restaurante existente."""
    db_restaurante = crud.update_restaurante(db, restaurante_id=restaurante_id, restaurante_update=restaurante_update)
    if db_restaurante is None:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    return db_restaurante

@app.delete(
    "/restaurantes/{restaurante_id}", 
    summary="Deletar Restaurante", 
    tags=["Restaurantes"],
    status_code=status.HTTP_204_NO_CONTENT
)
def deletar_restaurante(restaurante_id: uuid.UUID, db: Session = Depends(get_db)):
    """Deleta um restaurante do banco de dados. Esta operação é irreversível."""
    db_restaurante = crud.delete_restaurante(db, restaurante_id=restaurante_id)
    if db_restaurante is None:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    return {"message": "Restaurante deletado com sucesso"}

# CATEGORIAS
@app.post(
    "/categorias/", 
    response_model=schemas.Categoria, 
    summary="Criar Categoria", 
    tags=["Categorias"],
    status_code=status.HTTP_201_CREATED
)
def criar_categoria(categoria: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    """Cria uma nova categoria de produtos (ex: Pizzas, Bebidas)."""
    return crud.create_categoria(db=db, categoria=categoria)

@app.get(
    "/categorias/", 
    response_model=List[schemas.Categoria], 
    summary="Listar Categorias", 
    tags=["Categorias"]
)
def listar_categorias(
    skip: int = Query(0, description="Número de itens a pular (offset)"), 
    limit: int = Query(100, description="Número máximo de itens a retornar"), 
    db: Session = Depends(get_db)
):
    """Retorna uma lista de todas as categorias de produtos cadastradas."""
    categorias = crud.get_categorias(db, skip=skip, limit=limit)
    return categorias

# PRODUTOS
@app.post(
    "/produtos/", 
    response_model=schemas.Produto, 
    summary="Criar Produto", 
    tags=["Produtos"],
    status_code=status.HTTP_201_CREATED
)
def criar_produto(produto: schemas.ProdutoCreate, db: Session = Depends(get_db)):
    """Cria um novo produto associado a um restaurante e categoria."""
    return crud.create_produto(db=db, produto=produto)

@app.get(
    "/produtos/restaurante/{restaurante_id}", 
    response_model=List[schemas.Produto], 
    summary="Listar Produtos por Restaurante", 
    tags=["Produtos"]
)
def listar_produtos_restaurante(
    restaurante_id: uuid.UUID, 
    skip: int = Query(0, description="Número de itens a pular (offset)"), 
    limit: int = Query(100, description="Número máximo de itens a retornar"), 
    db: Session = Depends(get_db)
):
    """Retorna todos os produtos de um restaurante específico."""
    produtos = crud.get_produtos_by_restaurante(db, restaurante_id=restaurante_id, skip=skip, limit=limit)
    return produtos

@app.get(
    "/produtos/{produto_id}", 
    response_model=schemas.Produto, 
    summary="Obter Produto por ID", 
    tags=["Produtos"]
)
def obter_produto(produto_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retorna os detalhes de um produto específico pelo seu ID."""
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return db_produto

@app.put(
    "/produtos/{produto_id}", 
    response_model=schemas.Produto, 
    summary="Atualizar Produto", 
    tags=["Produtos"]
)
def atualizar_produto(produto_id: uuid.UUID, produto_update: schemas.ProdutoUpdate, db: Session = Depends(get_db)):
    """Atualiza as informações de um produto existente."""
    db_produto = crud.update_produto(db, produto_id=produto_id, produto_update=produto_update)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return db_produto

@app.delete(
    "/produtos/{produto_id}", 
    summary="Deletar Produto", 
    tags=["Produtos"],
    status_code=status.HTTP_204_NO_CONTENT
)
def deletar_produto(produto_id: uuid.UUID, db: Session = Depends(get_db)):
    """Deleta um produto do banco de dados. Esta operação é irreversível."""
    db_produto = crud.delete_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return {"message": "Produto deletado com sucesso"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
