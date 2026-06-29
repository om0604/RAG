from database import get_supabase
from config import config

def upload_file_to_storage(file_path: str, destination_name: str) -> str:
    """
    Upload a local file to Supabase Storage.
    Returns the public URL of the uploaded file.
    """
    supabase = get_supabase()
    
    with open(file_path, 'rb') as f:
        # We use upsert=True to overwrite if the file already exists
        response = supabase.storage.from_(config.SUPABASE_BUCKET).upload(
            path=destination_name,
            file=f,
            file_options={"upsert": "true"}
        )
    
    # Get the public URL for the uploaded file
    public_url = supabase.storage.from_(config.SUPABASE_BUCKET).get_public_url(destination_name)
    return public_url

def upload_bytes_to_storage(file_bytes: bytes, destination_name: str) -> str:
    """
    Upload file bytes to Supabase Storage.
    Returns the public URL of the uploaded file.
    """
    supabase = get_supabase()
    
    response = supabase.storage.from_(config.SUPABASE_BUCKET).upload(
        path=destination_name,
        file=file_bytes,
        file_options={"upsert": "true"}
    )
    
    public_url = supabase.storage.from_(config.SUPABASE_BUCKET).get_public_url(destination_name)
    return public_url

def delete_file_from_storage(file_name: str):
    """
    Delete a file from Supabase Storage.
    """
    supabase = get_supabase()
    supabase.storage.from_(config.SUPABASE_BUCKET).remove([file_name])
