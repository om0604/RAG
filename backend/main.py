from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import chat, documents
from database import get_supabase

app = FastAPI(title="AI Document Intelligence Platform")

@app.get("/api/health")
def health_check():
    supabase = get_supabase()
    db_status = "disconnected"
    storage_status = "disconnected"
    try:
        supabase.table("documents").select("id").limit(1).execute()
        db_status = "connected"
        storage_status = "connected" # Since they use the same client/url
    except Exception:
        pass
        
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "storage": storage_status
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular routes
app.include_router(chat.router, tags=["chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
