import os
import re
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def clean_text(text: str) -> str:
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

from typing import Union
from io import BytesIO

def process_pdf(pdf_source: Union[str, BytesIO]):
    print("Processing PDF...")
    if isinstance(pdf_source, str):
        if not os.path.exists(pdf_source):
            print("PDF file not found!")
            return [], 0
        reader = PdfReader(pdf_source)
    else:
        reader = PdfReader(pdf_source)
        
    chunks = []
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len
    )

    chunk_id = 0
    page_count = len(reader.pages)
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
            
        cleaned_text = clean_text(text)
        
        page_chunks = text_splitter.split_text(cleaned_text)
        
        for chunk_text in page_chunks:
            chunks.append({
                "chunk_id": chunk_id,
                "page": page_num + 1,
                "content": chunk_text
            })
            chunk_id += 1
            
    print(f"Total chunks generated: {len(chunks)} across {page_count} pages")
    return chunks, page_count

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = os.path.join(os.path.dirname(__file__), "data", "swiggy_annual_report.pdf")
    
    chunks, page_count = process_pdf(pdf_path)
    if chunks:
        print(f"Sample chunk: {chunks[0]}")
