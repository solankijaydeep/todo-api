from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import models
import schemas
import crud
from rag_service import ask_question_about_pdf, index_pdf_document
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal, run_migrations

# Perform automatic database check/alteration for new columns
run_migrations()

# Create tables if they do not exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/todos", response_model=schemas.TodoResponse)
def create_todo(
    todo: schemas.TodoCreate,
    db: Session = Depends(get_db)
):
    return crud.create_todo(db, todo)


@app.get("/todos", response_model=list[schemas.TodoResponse])
def get_todos(
    db: Session = Depends(get_db)
):
    return crud.get_todos(db)


@app.get("/todos/{todo_id}",
          response_model=schemas.TodoResponse)
def get_todo(
    todo_id: int,
    db: Session = Depends(get_db)
):
    todo = crud.get_todo(db, todo_id)

    if not todo:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    return todo


@app.put("/todos/{todo_id}",
         response_model=schemas.TodoResponse)
def update_todo(
    todo_id: int,
    todo: schemas.TodoUpdate,
    db: Session = Depends(get_db)
):
    updated = crud.update_todo(
        db,
        todo_id,
        todo
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    return updated


@app.delete("/todos/{todo_id}")
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db)
):
    deleted = crud.delete_todo(
        db,
        todo_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    return {"message": "Todo deleted"}


@app.post("/rag/pdf", response_model=schemas.PdfUploadResponse)
def upload_pdf_for_rag(file: UploadFile = File(...)):
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    try:
        return index_pdf_document(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/rag/pdf/{document_id}/ask", response_model=schemas.PdfQuestionResponse)
def ask_pdf_question(document_id: str, payload: schemas.PdfQuestionRequest):
    try:
        return ask_question_about_pdf(document_id, payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
