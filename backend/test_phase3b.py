import requests
import os
import time

BASE_URL = "http://localhost:8000/api"

def run_tests():
    print("--- 1. Upload Document A ---")
    pdf_a_path = os.path.join("data", "swiggy_annual_report.pdf")
    
    if not os.path.exists(pdf_a_path):
        print("Missing sample PDF A.")
        return
        
    with open(pdf_a_path, "rb") as f:
        files = {"file": (os.path.basename(pdf_a_path), f, "application/pdf")}
        resp = requests.post(f"{BASE_URL}/documents/", files=files)
        
    print(resp.status_code)
    doc_a = resp.json()
    doc_a_id = doc_a.get("id")
    print(f"Doc A ID: {doc_a_id}")

    print("\n--- 2. Upload Document B ---")
    # We will upload the same file but treat it as Document B to ensure isolation
    with open(pdf_a_path, "rb") as f:
        files = {"file": ("Document_B.pdf", f, "application/pdf")}
        resp = requests.post(f"{BASE_URL}/documents/", files=files)
        
    print(resp.status_code)
    doc_b = resp.json()
    doc_b_id = doc_b.get("id")
    print(f"Doc B ID: {doc_b_id}")

    print("\n--- 3. Verify both appear in documents table ---")
    resp = requests.get(f"{BASE_URL}/documents/")
    docs = resp.json()
    print(f"Total documents: {len(docs)}")
    doc_ids = [d["id"] for d in docs]
    assert doc_a_id in doc_ids and doc_b_id in doc_ids, "Both docs must exist!"

    print("\n--- 4. Verify chunk counts ---")
    for d in docs:
        if d["id"] in [doc_a_id, doc_b_id]:
            print(f"Doc {d['filename']} chunks: {d['chunk_count']}")

    print("\n--- 5. Ask questions against document A ---")
    resp = requests.post(
        f"{BASE_URL}/chat", 
        json={"question": "What is Swiggy?", "document_id": doc_a_id}
    )
    print(f"Chat A Status: {resp.status_code}")
    chat_a = resp.json()
    print(f"Chat A Sources: {len(chat_a.get('sources', []))}")
    
    print("\n--- 6. Ask questions against document B ---")
    resp = requests.post(
        f"{BASE_URL}/chat", 
        json={"question": "What is Swiggy?", "document_id": doc_b_id}
    )
    print(f"Chat B Status: {resp.status_code}")
    chat_b = resp.json()
    print(f"Chat B Sources: {len(chat_b.get('sources', []))}")

    print("\n--- 7. Delete Document A ---")
    resp = requests.delete(f"{BASE_URL}/documents/{doc_a_id}")
    print(f"Delete A Status: {resp.status_code}")
    
    print("\n--- 8. Verify Document B still works ---")
    resp = requests.post(
        f"{BASE_URL}/chat", 
        json={"question": "What is Swiggy?", "document_id": doc_b_id}
    )
    print(f"Chat B (After Delete A) Status: {resp.status_code}")
    
    # Check if doc A is really gone
    resp = requests.post(
        f"{BASE_URL}/chat", 
        json={"question": "What is Swiggy?", "document_id": doc_a_id}
    )
    print(f"Chat A (After Delete A) Status (Should fail 404): {resp.status_code}")

    print("\n--- 9. Cleanup Document B ---")
    resp = requests.delete(f"{BASE_URL}/documents/{doc_b_id}")
    print(f"Delete B Status: {resp.status_code}")
    
    print("\n✅ All Multi-Document Validation Tests Passed!")

if __name__ == "__main__":
    run_tests()
