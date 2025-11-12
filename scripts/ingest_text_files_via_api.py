"""
Ingest text files using the ingest API endpoint
This is the proper way to ensure documents are processed
"""

import os
import sys
import requests
from pathlib import Path

# Get backend URL from environment or use default
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def ingest_file(file_path: str, filename: str):
    """Ingest a file via the API"""
    print(f"\n{'='*60}")
    print(f"Processing: {filename}")
    print(f"{'='*60}")
    
    if not os.path.exists(file_path):
        print(f"[X] File not found: {file_path}")
        return False
    
    # Read file
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    print(f"File size: {len(file_content)} bytes")
    
    # Prepare request
    url = f"{BACKEND_URL}/api/v1/ingest/bulk-pdfs"
    files = {
        'files': (filename, file_content, 'text/plain')
    }
    headers = {
        'X-User-ID': '00000000-0000-0000-0000-000000000001',
        'X-Project-ID': '00000000-0000-0000-0000-000000000002'
    }
    
    print(f"\nSending to: {url}")
    print(f"Headers: {headers}")
    
    try:
        response = requests.post(url, files=files, headers=headers, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n[OK] Response received")
            print(f"   Files processed: {data.get('files_processed', 0)}")
            print(f"   Files successful: {data.get('files_successful', 0)}")
            print(f"   Total chunks: {data.get('total_chunks_created', 0)}")
            
            # Check individual file results
            for result in data.get('results', []):
                if result.get('filename') == filename:
                    if result.get('success'):
                        print(f"\n[OK] {filename} ingested successfully!")
                        print(f"   Chunks created: {result.get('chunks_created', 0)}")
                        return True
                    else:
                        print(f"\n[X] {filename} failed: {result.get('error', 'Unknown error')}")
                        return False
            
            return data.get('files_successful', 0) > 0
        else:
            print(f"\n[X] HTTP Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"\n[X] Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Main function"""
    print("="*60)
    print("TEXT FILE INGESTION VIA API")
    print("="*60)
    print(f"\nBackend URL: {BACKEND_URL}")
    print("Note: Make sure the backend is running!")
    
    # Get script directory
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    
    # File paths
    files = [
        (backend_dir / "simon_personal_description.txt", "simon_personal_description.txt"),
        (backend_dir / "document_explanation_guide.txt", "document_explanation_guide.txt")
    ]
    
    results = []
    for file_path, filename in files:
        success = ingest_file(str(file_path), filename)
        results.append(success)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Files processed: {successful}/{total}")
    
    if successful == total:
        print("\n[OK] All files ingested successfully!")
        print("\nNext steps:")
        print("1. Wait 5-10 seconds for embeddings to be stored")
        print("2. Test with: 'What's my tone?'")
        print("3. Test with: 'Tell me about yourself'")
        print("4. Run: python scripts/check_document_ingestion.py")
    else:
        print("\n[WARN] Some files failed to ingest")
        print("Check the error messages above")
        print("\nAlternative: Use the frontend upload and check backend logs")

if __name__ == "__main__":
    main()

