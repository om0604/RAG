import requests
import os
import time

BASE_URL = "http://localhost:8000/api"

def run_tests():
    print("--- 1. Testing /api/health ---")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Health Status Code: {resp.status_code}")
    print(f"Health Response: {resp.json()}")

    print("\n--- 2. Testing /api/documents (GET before upload) ---")
    resp = requests.get(f"{BASE_URL}/documents/")
    print(f"Docs Status Code: {resp.status_code}")
    
    print("\n--- 3. Testing /api/documents (POST - Invalid File) ---")
    files = {"file": ("test.txt", b"Hello world", "text/plain")}
    resp = requests.post(f"{BASE_URL}/documents/", files=files)
    print(f"Invalid POST Status Code: {resp.status_code}")
    print(f"Invalid POST Response: {resp.json()}")

    print("\n--- 4. Testing /api/documents (POST - Valid PDF) ---")
    pdf_path = os.path.join("data", "swiggy_annual_report.pdf")
    if not os.path.exists(pdf_path):
        # Find any PDF
        for f in os.listdir("data"):
            if f.endswith(".pdf"):
                pdf_path = os.path.join("data", f)
                break
                
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
            resp = requests.post(f"{BASE_URL}/documents/", files=files)
        print(f"Valid POST Status Code: {resp.status_code}")
        try:
            doc_data = resp.json()
            print(f"Valid POST Response: {doc_data}")
            doc_id = doc_data.get("id")
        except Exception as e:
            print("Failed to parse POST JSON", resp.text)
            doc_id = None
    else:
        print("No sample PDF found to test upload.")
        doc_id = None

    if doc_id:
        print("\n--- 5. Testing /api/documents (GET after upload) ---")
        resp = requests.get(f"{BASE_URL}/documents/")
        print(f"Docs Status Code: {resp.status_code}")
        docs = resp.json()
        print(f"Docs length: {len(docs)}")
        if len(docs) > 0:
            print(f"First doc metadata keys: {list(docs[0].keys())}")
            print(f"First doc size: {docs[0].get('size_bytes')}")

        print("\n--- 6. Testing /api/documents (DELETE) ---")
        resp = requests.delete(f"{BASE_URL}/documents/{doc_id}")
        print(f"DELETE Status Code: {resp.status_code}")
        print(f"DELETE Response: {resp.json()}")
    
if __name__ == "__main__":
    run_tests()
