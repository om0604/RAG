from supabase import create_client, Client
from config import config

# Initialize Supabase client lazily
_supabase: Client = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")
        _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase

def get_db():
    # Placeholder for direct SQLAlchemy/asyncpg connections if needed later.
    # Currently we rely on get_supabase() for DB operations via PostgREST.
    pass
