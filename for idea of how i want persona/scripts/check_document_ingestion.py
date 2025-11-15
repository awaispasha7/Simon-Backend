"""
Check if documents were properly ingested
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database.supabase import get_supabase_client

def check_documents():
    """Check if documents are in the database"""
    print("=" * 60)
    print("DOCUMENT INGESTION CHECK")
    print("=" * 60)
    print()
    
    supabase = get_supabase_client()
    if not supabase:
        print("[X] Supabase not configured")
        return
    
    # Check document_embeddings table
    print("1. Checking document_embeddings table...")
    try:
        result = supabase.table("document_embeddings").select("embedding_id, chunk_text, metadata").limit(20).execute()
        
        if result.data:
            print(f"   [OK] Found {len(result.data)} document chunks")
            
            # Group by filename
            filenames = {}
            for chunk in result.data:
                filename = chunk.get('metadata', {}).get('filename', 'Unknown')
                if filename not in filenames:
                    filenames[filename] = 0
                filenames[filename] += 1
            
            print()
            print("   Documents found:")
            for filename, count in filenames.items():
                print(f"   - {filename}: {count} chunks")
            
            # Check for our new documents
            print()
            print("2. Checking for new documents...")
            new_docs = [
                "simon_personal_description.txt",
                "document_explanation_guide.txt"
            ]
            
            found_new = False
            for doc_name in new_docs:
                found = False
                for filename in filenames.keys():
                    if doc_name.lower() in filename.lower():
                        print(f"   [OK] Found: {filename} ({filenames[filename]} chunks)")
                        found = True
                        found_new = True
                        break
                if not found:
                    print(f"   [X] Not found: {doc_name}")
            
            if not found_new:
                print()
                print("   [WARN] New documents not found in database!")
                print("   -> Documents may still be processing")
                print("   -> Check upload logs for processing status")
            
        else:
            print("   [X] No document chunks found in database")
            print("   -> Documents may not have been ingested")
    
    except Exception as e:
        print(f"   [X] Error checking documents: {e}")
        import traceback
        print(traceback.format_exc())
    
    print()
    print("3. Testing RPC function...")
    try:
        # Create a dummy embedding
        dummy_embedding = [0.0] * 1536
        
        result = supabase.rpc(
            'get_similar_document_chunks',
            {
                'query_embedding': dummy_embedding,
                'query_user_id': '00000000-0000-0000-0000-000000000001',
                'query_project_id': None,
                'match_count': 5,
                'similarity_threshold': 0.01
            }
        ).execute()
        
        if result.data:
            print(f"   [OK] RPC function works - returned {len(result.data)} chunks")
        else:
            print("   [WARN] RPC function returned 0 chunks")
            print("   -> This might be normal if similarity is too low")
    
    except Exception as e:
        print(f"   [X] RPC function error: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    check_documents()

