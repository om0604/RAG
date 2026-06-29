from fastapi import APIRouter, HTTPException
from schemas.chat import QuestionRequest, AnswerResponse, Source
from services.rag_service import retrieve, generate_answer
from config import config
from database import get_supabase

router = APIRouter()

@router.post("/ask", response_model=AnswerResponse)
@router.post("/api/chat", response_model=AnswerResponse)
def ask_question(req: QuestionRequest):
    supabase = get_supabase()
    
    document_id = req.document_id
    
    try:
        if not document_id:
            # Fallback for legacy frontend: get the most recent 'Ready' document
            doc_resp = supabase.table("documents").select("id").eq("status", "Ready").order("created_at", desc=True).limit(1).execute()
            if not doc_resp.data:
                raise HTTPException(status_code=404, detail="No ready documents found to query.")
            document_id = doc_resp.data[0]["id"]
        else:
            # Validate provided document exists and is ready
            doc_resp = supabase.table("documents").select("status").eq("id", document_id).execute()
            if not doc_resp.data:
                raise HTTPException(status_code=404, detail="Document not found.")
            if doc_resp.data[0]["status"] != "Ready":
                raise HTTPException(status_code=400, detail="Document is not ready for querying.")
                
        chunks = retrieve(req.question, document_id=document_id, top_k=5)
        
        if not chunks or chunks[0]['score'] > config.SIMILARITY_THRESHOLD:
            return AnswerResponse(
                answer="Insufficient information found in the provided document.",
                sources=[]
            )
            
        answer = generate_answer(req.question, chunks)
        
        sources = [
            Source(page=c['page'], content=c['content'], score=c['score']) 
            for c in chunks
        ]
        
        return AnswerResponse(
            answer=answer,
            sources=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred during chat processing.")
