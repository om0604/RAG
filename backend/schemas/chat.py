from pydantic import BaseModel
from typing import List, Optional

class QuestionRequest(BaseModel):
    question: str
    document_id: Optional[str] = None

class Source(BaseModel):
    page: int
    content: str
    score: float

class AnswerResponse(BaseModel):
    answer: str
    sources: List[Source]
