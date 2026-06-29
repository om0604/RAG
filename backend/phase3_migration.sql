-- Phase 3A Migration: Add metadata columns to documents table

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS size_bytes BIGINT DEFAULT 0,
ADD COLUMN IF NOT EXISTS page_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS chunk_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS file_type TEXT DEFAULT 'application/pdf';

-- Drop the old RPC function so we can recreate it with the new filter_document_id param
DROP FUNCTION IF EXISTS match_document_chunks(vector, double precision, integer);

-- Recreate the RPC function to allow filtering by document_id (optional for now, but foundation for Phase 3B)
create or replace function match_document_chunks (
  query_embedding vector(384),
  match_threshold float,
  match_count int,
  filter_document_id uuid DEFAULT NULL
)
returns table (
  id uuid,
  document_id uuid,
  page_number integer,
  chunk_number integer,
  content text,
  score float
)
language sql stable
as $$
  select
    document_chunks.id,
    document_chunks.document_id,
    document_chunks.page_number,
    document_chunks.chunk_number,
    document_chunks.content,
    (document_chunks.embedding <-> query_embedding) as score
  from document_chunks
  where (document_chunks.embedding <-> query_embedding) <= match_threshold
    and (filter_document_id IS NULL OR document_chunks.document_id = filter_document_id)
  order by document_chunks.embedding <-> query_embedding
  limit match_count;
$$;
