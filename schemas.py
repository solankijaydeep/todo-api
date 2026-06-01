from pydantic import BaseModel
from typing import Optional

class TodoCreate(BaseModel):
    title: str
    category: Optional[str] = None

class TodoUpdate(BaseModel):
    title: str
    completed: bool
    category: Optional[str] = None

class TodoResponse(BaseModel):
    id: int
    title: str
    completed: bool
    category: Optional[str] = None

    class Config:
        from_attributes = True


class PdfUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_indexed: int
    message: str


class PdfQuestionRequest(BaseModel):
    question: str


class PdfSourceChunk(BaseModel):
    chunk_index: int
    page_number: Optional[int] = None
    score: float
    text: str


class PdfQuestionResponse(BaseModel):
    document_id: str
    question: str
    answer: str
    sources: list[PdfSourceChunk]
