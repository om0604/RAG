from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict, Any
from config import config
from database import get_supabase
from storage import upload_file_to_storage
import io
import time

router = APIRouter()

@router.get("/")
def get_documents():
    """List all uploaded documents."""
    supabase = get_supabase()
    try:
        response = supabase.table("documents").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/")
async def upload_document(file: UploadFile = File(...)):
    """Upload a new PDF document and process it."""
    # Lazy imports
    from ingest import process_pdf
    from services.rag_service import build_index
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Unsupported file type. Only PDF is allowed.")
        
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
        
    size_bytes = len(file_bytes)
    # Validate 25MB max size
    if size_bytes > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 25 MB.")

    supabase = get_supabase()
    
    # Generate unique storage path
    timestamp = int(time.time())
    storage_path = f"reports/{timestamp}_{file.filename}"
    
    try:
        # 1. Insert initial row into documents table
        doc_insert = supabase.table("documents").insert({
            "filename": file.filename,
            "storage_path": storage_path,
            "status": "Processing",
            "size_bytes": size_bytes,
            "file_type": file.content_type or "application/pdf"
        }).execute()
        
        document_id = doc_insert.data[0]["id"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create document record: {str(e)}")

    try:
        # 2. Upload to Supabase Storage
        # The upload_file_to_storage currently takes a file_path, we need to adapt or just write temporary file
        # But wait, storage.py might not accept bytes! We will need to update storage.py to accept bytes.
        from storage import upload_bytes_to_storage
        upload_bytes_to_storage(file_bytes, storage_path)
        
        # 3. Extract chunks from bytes
        pdf_stream = io.BytesIO(file_bytes)
        chunks, page_count = process_pdf(pdf_stream)
        
        if not chunks:
            raise Exception("No readable text found in PDF.")
            
        # 4. Build index
        build_index(chunks, document_id)
        
        # 5. Update metadata
        supabase.table("documents").update({
            "status": "Ready",
            "page_count": page_count,
            "chunk_count": len(chunks)
        }).eq("id", document_id).execute()
        
        return {"id": document_id, "filename": file.filename}
        
    except Exception as e:
        # Rollback: Update status to Failed
        try:
            supabase.table("documents").update({"status": "Failed"}).eq("id", document_id).execute()
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
def delete_document(document_id: str):
    """Delete a document, its chunks (via DB cascade), and the Storage file."""
    supabase = get_supabase()
    
    try:
        # Get the storage path first
        doc_resp = supabase.table("documents").select("storage_path").eq("id", document_id).execute()
        if not doc_resp.data:
            raise HTTPException(status_code=404, detail="Document not found.")
            
        storage_path = doc_resp.data[0]["storage_path"]
        
        # Delete from storage
        from storage import delete_file_from_storage
        try:
            delete_file_from_storage(storage_path)
        except Exception as e:
            print(f"Warning: Failed to delete from storage {storage_path}: {e}")
            
        # Delete from database
        supabase.table("documents").delete().eq("id", document_id).execute()
        
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
