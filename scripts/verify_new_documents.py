"""
Verify the newly ingested documents are in the database
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database.supabase import get_supabase_client

def verify():
    supabase = get_supabase_client()
    if not supabase:
        print("[X] Supabase not configured")
        return
    
    # Get ALL document chunks (no limit)
    print("Checking all document chunks...")
    result = supabase.table("document_embeddings").select("embedding_id, chunk_text, metadata").execute()
    
    print(f"Total chunks in database: {len(result.data)}")
    
    # Group by filename
    filenames = {}
    for chunk in result.data:
        metadata = chunk.get('metadata', {})
        filename = metadata.get('filename', 'Unknown')
        if filename not in filenames:
            filenames[filename] = {
                'count': 0,
                'chunks': []
            }
        filenames[filename]['count'] += 1
        filenames[filename]['chunks'].append({
            'embedding_id': chunk.get('embedding_id'),
            'preview': chunk.get('chunk_text', '')[:100]
        })
    
    print(f"\nFound {len(filenames)} unique documents:\n")
    
    for filename, data in sorted(filenames.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"{filename}: {data['count']} chunks")
        if 'simon' in filename.lower() or 'document_explanation' in filename.lower():
            print(f"  -> This is one of the new documents!")
            print(f"  -> First chunk preview: {data['chunks'][0]['preview'][:150]}...")
    
    # Check specifically for our documents
    print("\n" + "="*60)
    print("Checking for new documents specifically...")
    print("="*60)
    
    new_docs_found = False
    for filename in filenames.keys():
        if 'simon_personal_description' in filename.lower():
            print(f"\n[OK] Found: {filename}")
            print(f"   Chunks: {filenames[filename]['count']}")
            new_docs_found = True
        if 'document_explanation' in filename.lower():
            print(f"\n[OK] Found: {filename}")
            print(f"   Chunks: {filenames[filename]['count']}")
            new_docs_found = True
    
    if not new_docs_found:
        print("\n[X] New documents not found by filename search")
        print("   They might be stored with different metadata")
        print("   Checking all recent chunks...")
        
        # Check recent chunks (by created_at if available)
        recent = supabase.table("document_embeddings").select("*").order("created_at", desc=True).limit(50).execute()
        print(f"   Found {len(recent.data)} recent chunks")
        
        for chunk in recent.data[:10]:
            metadata = chunk.get('metadata', {})
            filename = metadata.get('filename', 'No filename')
            preview = chunk.get('chunk_text', '')[:100]
            print(f"   - {filename}: {preview}...")

if __name__ == "__main__":
    verify()

