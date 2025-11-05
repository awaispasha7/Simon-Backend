"""
Bulk PDF Ingestion Script for Single User
Ingests all PDFs from a directory into RAG system
"""

import os
import sys
import requests
from pathlib import Path
from typing import List

# Configuration
BACKEND_URL = "http://127.0.0.1:8000"
INGEST_ENDPOINT = f"{BACKEND_URL}/api/v1/ingest/bulk-pdfs"

# Single user ID for personal assistant
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000002"


def ingest_pdfs_from_directory(directory_path: str) -> dict:
    """
    Ingests all PDF files from a directory
    
    Args:
        directory_path: Path to directory containing PDFs
    
    Returns:
        Summary of ingestion results
    """
    pdf_path = Path(directory_path)
    
    if not pdf_path.exists():
        print(f"[ERROR] Directory not found: {directory_path}")
        return {"error": "Directory not found"}
    
    # Find all PDF files
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"[ERROR] No PDF files found in: {directory_path}")
        return {"error": "No PDF files found"}
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    print(f"Directory: {directory_path}")
    print(f"User ID: {DEFAULT_USER_ID}")
    print(f"Project ID: {DEFAULT_PROJECT_ID}")
    print("-" * 60)
    
    # Prepare files for upload
    files = []
    for pdf_file in pdf_files:
        print(f"Adding: {pdf_file.name}")
        files.append(
            ("files", (pdf_file.name, open(pdf_file, "rb"), "application/pdf"))
        )
    
    # Upload all PDFs
    try:
        headers = {
            "X-User-ID": DEFAULT_USER_ID,
            "X-Project-ID": DEFAULT_PROJECT_ID
        }
        
        print(f"\nUploading {len(files)} PDF(s) to RAG system...")
        response = requests.post(INGEST_ENDPOINT, headers=headers, files=files)
        
        # Close file handles
        for _, file_tuple in files:
            file_tuple[1].close()
        
        if response.status_code == 200:
            result = response.json()
            print("\n[SUCCESS] Ingestion Complete!")
            print("-" * 60)
            print(f"Files processed: {result.get('files_processed', 0)}")
            print(f"Files successful: {result.get('files_successful', 0)}")
            print(f"Files failed: {result.get('files_failed', 0)}")
            print(f"Total chunks created: {result.get('total_chunks_created', 0)}")
            print("-" * 60)
            
            # Show individual results
            if result.get('results'):
                print("\nIndividual File Results:")
                for file_result in result['results']:
                    status = "[OK]" if file_result.get('success') else "[FAIL]"
                    filename = file_result.get('filename', 'unknown')
                    chunks = file_result.get('chunks_created', 0)
                    error = file_result.get('error')
                    
                    print(f"  {status} {filename}: {chunks} chunks", end="")
                    if error:
                        print(f" - Error: {error}")
                    else:
                        print()
            
            return result
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            print(f"[ERROR] Ingestion failed: {error_msg}")
            return {"error": error_msg}
            
    except Exception as e:
        print(f"[ERROR] Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def verify_ingestion():
    """Verify embeddings were created"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/ingest/status")
        if response.status_code == 200:
            status = response.json()
            print("\nVerification:")
            print("-" * 60)
            print(f"Total embeddings: {status.get('embeddings_count', 0)}")
            print(f"Total assets: {status.get('assets_count', 0)}")
            
            if status.get('embeddings_by_user'):
                print(f"\nEmbeddings by user:")
                for user_id, count in status['embeddings_by_user'].items():
                    print(f"  - {user_id}: {count} embeddings")
            
            if status.get('embeddings_by_type'):
                print(f"\nEmbeddings by type:")
                for doc_type, count in status['embeddings_by_type'].items():
                    print(f"  - {doc_type}: {count} embeddings")
            
            return status
        else:
            print(f"[ERROR] Failed to verify: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Error verifying: {e}")
        return None


if __name__ == "__main__":
    # Fix Windows encoding for emojis
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    if len(sys.argv) < 2:
        print("Usage: python ingest_all_pdfs.py <directory_path>")
        print("\nExample:")
        print("  python ingest_all_pdfs.py ./client_pdfs")
        print("  python ingest_all_pdfs.py C:/Users/Admin/Documents/PDFs")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    print("=" * 60)
    print("Bulk PDF Ingestion for Personal Assistant")
    print("=" * 60)
    print()
    
    # Ingest PDFs
    result = ingest_pdfs_from_directory(directory)
    
    if result and not result.get('error'):
        # Verify ingestion
        verify_ingestion()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] Ready to test RAG retrieval in chat!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start a chat session")
        print("2. Ask questions about your PDF content")
        print("3. Verify AI references your documents")
        print("\nTest query examples:")
        print("  - 'What did you learn from my documents?'")
        print("  - 'Summarize the key points from my PDFs'")
        print("  - 'What are the main strategies mentioned?'")

