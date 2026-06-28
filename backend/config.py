import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

class Config:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "1.5"))
    INDEX_FILE: str = os.getenv("INDEX_FILE", "faiss_index.index")
    METADATA_FILE: str = os.getenv("METADATA_FILE", "metadata.pkl")
    
    # Supabase Phase 2 Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "documents")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Base directory of the backend to resolve paths robustly
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")

config = Config()
