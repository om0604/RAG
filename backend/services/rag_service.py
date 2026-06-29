from sentence_transformers import SentenceTransformer
from config import config
from database import get_supabase

# Load embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def build_index(chunks, document_id: str):
    """Generate embeddings and insert them into Supabase document_chunks table"""
    print(f"Generating embeddings for {len(chunks)} chunks...")
    texts = [chunk['content'] for chunk in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True)
    
    supabase = get_supabase()
    
    # Insert in batches to prevent huge HTTP payloads
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_embeddings = embeddings[i:i + batch_size]
        
        data = []
        for j, chunk in enumerate(batch_chunks):
            data.append({
                "document_id": document_id,
                "page_number": chunk['page'],
                "chunk_number": i + j,
                "content": chunk['content'],
                "embedding": batch_embeddings[j].tolist()
            })
        
        supabase.table("document_chunks").insert(data).execute()
        
    print(f"Saved {len(chunks)} chunks to Supabase pgvector.")

def retrieve(query: str, document_id: str, top_k: int = 5):
    """Retrieve nearest neighbor chunks via Supabase RPC"""
    supabase = get_supabase()
    
    query_embedding = embedder.encode([query])[0].tolist()
    
    # Call the RPC function for vector similarity search
    response = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": config.SIMILARITY_THRESHOLD,
            "match_count": top_k,
            "filter_document_id": document_id
        }
    ).execute()
    
    results = []
    for item in response.data:
        # Map the DB schema back to the dictionary expected by the frontend
        results.append({
            "page": item["page_number"],
            "content": item["content"],
            "score": item["score"]
        })
            
    return results

def generate_answer(query, contexts):
    prompt_template = """You are an AI Document Assistant.

Answer the question ONLY using the provided context.
If the answer is not found in the context, respond:
"The answer is not available in the provided document."

Context:
{context}

Question:
{question}

Answer:"""
    
    context_text = "\n\n".join([f"Page {c['page']}:\n{c['content']}" for c in contexts])
    formatted_prompt = prompt_template.format(context=context_text, question=query)
    
    try:
        from groq import Groq
        client = Groq(api_key=config.GROQ_API_KEY)
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": formatted_prompt}],
            model=config.GROQ_MODEL,
            temperature=0,
            max_tokens=500,
        )
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        return f"Error connecting to Groq API: {str(e)}"
