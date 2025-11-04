from sqlalchemy.orm import Session
import models
import schemas
import uuid
from typing import List, Optional

# CRUD Restaurantes
def create_restaurante(db: Session, restaurante: schemas.RestauranteCreate):
    db_restaurante = models.Restaurante(**restaurante.dict())
    db.add(db_restaurante)
    db.commit()
    db.refresh(db_restaurante)
    return db_restaurante

def get_restaurante(db: Session, restaurante_id: uuid.UUID):
    return db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()

def get_restaurante_by_cnpj(db: Session, cnpj: str):
    return db.query(models.Restaurante).filter(models.Restaurante.cnpj == cnpj).first()

def get_restaurantes(db: Session, skip: int = 0, limit: int = 100, ativo: bool = True):
    query = db.query(models.Restaurante)
    if ativo:
        query = query.filter(models.Restaurante.ativo == True)
    return query.offset(skip).limit(limit).all()

def update_restaurante(db: Session, restaurante_id: uuid.UUID, restaurante_update: schemas.RestauranteUpdate):
    db_restaurante = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if db_restaurante:
        update_data = restaurante_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_restaurante, field, value)
        db.commit()
        db.refresh(db_restaurante)
    return db_restaurante

def delete_restaurante(db: Session, restaurante_id: uuid.UUID):
    db_restaurante = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if db_restaurante:
        db.delete(db_restaurante)
        db.commit()
    return db_restaurante

# CRUD Categorias
def create_categoria(db: Session, categoria: schemas.CategoriaCreate):
    db_categoria = models.Categoria(**categoria.dict())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def get_categorias(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Categoria).offset(skip).limit(limit).all()

# CRUD Produtos
def create_produto(db: Session, produto: schemas.ProdutoCreate):
    db_produto = models.Produto(**produto.dict())
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto

def get_produto(db: Session, produto_id: uuid.UUID):
    return db.query(models.Produto).filter(models.Produto.id == produto_id).first()

def get_produtos_by_restaurante(db: Session, restaurante_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.Produto).filter(
        models.Produto.restaurante_id == restaurante_id
    ).offset(skip).limit(limit).all()

def update_produto(db: Session, produto_id: uuid.UUID, produto_update: schemas.ProdutoUpdate):
    db_produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if db_produto:
        update_data = produto_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_produto, field, value)
        db.commit()
        db.refresh(db_produto)
    return db_produto

def delete_produto(db: Session, produto_id: uuid.UUID):
    db_produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if db_produto:
        db.delete(db_produto)
        db.commit()
    return db_produto