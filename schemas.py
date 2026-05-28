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