from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import crud, schemas, models
from database import SessionLocal, engine, get_db
import uuid
from typing import List

# Criar tabelas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Restaurantes Service",
    description="Microsserviço para gerenciamento de restaurantes e produtos",
    version="1.0.0"
)

# RESTAURANTES
@app.post("/restaurantes/", response_model=schemas.Restaurante)
def criar_restaurante(restaurante: schemas.RestauranteCreate, db: Session = Depends(get_db)):
    db_restaurante = crud.get_restaurante_by_cnpj(db, cnpj=restaurante.cnpj)
    if db_restaurante:
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    return crud.create_restaurante(db=db, restaurante=restaurante)

@app.get("/restaurantes/", response_model=List[schemas.Restaurante])
def listar_restaurantes(skip: int = 0, limit: int = 100, ativo: bool = True, db: Session = Depends(get_db)):
    restaurantes = crud.get_restaurantes(db, skip=skip, limit=limit, ativo=ativo)
    return restaurantes

@app.get("/restaurantes/{restaurante_id}", response_model=schemas.Restaurante)
def obter_restaurante(restaurante_id: uuid.UUID, db: Session = Depends(get_db)):
    db_restaurante = crud.get_restaurante(db, restaurante_id=restaurante_id)
    if db_restaurante is None:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    return db_restaurante

@app.put("/restaurantes/{restaurante_id}", response_model=schemas.Restaurante)
def atualizar_restaurante(restaurante_id: uuid.UUID, restaurante_update: schemas.RestauranteUpdate, db: Session = Depends(get_db)):
    db_restaurante = crud.update_restaurante(db, restaurante_id=restaurante_id, restaurante_update=restaurante_update)
    if db_restaurante is None:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    return db_restaurante

@app.delete("/restaurantes/{restaurante_id}")
def deletar_restaurante(restaurante_id: uuid.UUID, db: Session = Depends(get_db)):
    db_restaurante = crud.delete_restaurante(db, restaurante_id=restaurante_id)
    if db_restaurante is None:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    return {"message": "Restaurante deletado com sucesso"}

# CATEGORIAS
@app.post("/categorias/", response_model=schemas.Categoria)
def criar_categoria(categoria: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    return crud.create_categoria(db=db, categoria=categoria)

@app.get("/categorias/", response_model=List[schemas.Categoria])
def listar_categorias(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    categorias = crud.get_categorias(db, skip=skip, limit=limit)
    return categorias

# PRODUTOS
@app.post("/produtos/", response_model=schemas.Produto)
def criar_produto(produto: schemas.ProdutoCreate, db: Session = Depends(get_db)):
    return crud.create_produto(db=db, produto=produto)

@app.get("/produtos/restaurante/{restaurante_id}", response_model=List[schemas.Produto])
def listar_produtos_restaurante(restaurante_id: uuid.UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    produtos = crud.get_produtos_by_restaurante(db, restaurante_id=restaurante_id, skip=skip, limit=limit)
    return produtos

@app.get("/produtos/{produto_id}", response_model=schemas.Produto)
def obter_produto(produto_id: uuid.UUID, db: Session = Depends(get_db)):
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return db_produto

@app.put("/produtos/{produto_id}", response_model=schemas.Produto)
def atualizar_produto(produto_id: uuid.UUID, produto_update: schemas.ProdutoUpdate, db: Session = Depends(get_db)):
    db_produto = crud.update_produto(db, produto_id=produto_id, produto_update=produto_update)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return db_produto

@app.delete("/produtos/{produto_id}")
def deletar_produto(produto_id: uuid.UUID, db: Session = Depends(get_db)):
    db_produto = crud.delete_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return {"message": "Produto deletado com sucesso"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)