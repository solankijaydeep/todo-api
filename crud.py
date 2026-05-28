from sqlalchemy.orm import Session
import models
import schemas
from openai_service import categorize_todo

def get_todos(db: Session):
    return db.query(models.Todo).all()

def get_todo(db: Session, todo_id: int):
    return db.query(models.Todo).filter(
        models.Todo.id == todo_id
    ).first()

def create_todo(db: Session, todo: schemas.TodoCreate):
    category = todo.category
    if not category:
        category = categorize_todo(todo.title)

    db_todo = models.Todo(
        title=todo.title,
        category=category
    )

    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)

    return db_todo

def update_todo(
    db: Session,
    todo_id: int,
    todo: schemas.TodoUpdate
):
    db_todo = get_todo(db, todo_id)

    if db_todo:
        db_todo.title = todo.title
        db_todo.completed = todo.completed
        if todo.category is not None:
            db_todo.category = todo.category

        db.commit()
        db.refresh(db_todo)

    return db_todo

def delete_todo(db: Session, todo_id: int):
    db_todo = get_todo(db, todo_id)

    if db_todo:
        db.delete(db_todo)
        db.commit()

    return db_todo