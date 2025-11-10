#!/usr/bin/env python3
"""
Script to remove BookYolo test documents from the database
Run this script to clean up test documents that shouldn't be in production
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app.database.supabase import get_supabase_client

def cleanup_bookyolo_documents():
    """Remove all BookYolo-related documents from the database"""
    supabase = get_supabase_client()
    
    if not supabase:
        print("❌ Supabase not configured. Cannot clean up documents.")
        return
    
    print("🔍 Searching for BookYolo documents...")
    
    # Step 1: Find document embeddings for BookYolo documents
    try:
        # Get all document embeddings that match BookYolo
        embeddings_result = supabase.table("document_embeddings").select("embedding_id, asset_id, metadata").execute()
        
        bookyolo_embeddings = []
        bookyolo_asset_ids = set()
        
        for embedding in embeddings_result.data:
            metadata = embedding.get('metadata', {})
            filename = metadata.get('filename', '')
            chunk_text = embedding.get('chunk_text', '')
            
            if ('BookYolo' in filename or 'Specifications_Final' in filename or
                'BookYolo' in chunk_text or 'BOOKYOLO' in chunk_text):
                bookyolo_embeddings.append(embedding['embedding_id'])
                if embedding.get('asset_id'):
                    bookyolo_asset_ids.add(embedding['asset_id'])
        
        print(f"📊 Found {len(bookyolo_embeddings)} BookYolo document embeddings")
        print(f"📊 Found {len(bookyolo_asset_ids)} unique asset IDs to delete")
        
        # Step 2: Delete document embeddings
        if bookyolo_embeddings:
            for embedding_id in bookyolo_embeddings:
                try:
                    supabase.table("document_embeddings").delete().eq("embedding_id", embedding_id).execute()
                except Exception as e:
                    print(f"⚠️ Failed to delete embedding {embedding_id}: {e}")
            
            print(f"✅ Deleted {len(bookyolo_embeddings)} document embeddings")
        
        # Step 3: Delete assets
        if bookyolo_asset_ids:
            for asset_id in bookyolo_asset_ids:
                try:
                    supabase.table("assets").delete().eq("id", asset_id).execute()
                except Exception as e:
                    print(f"⚠️ Failed to delete asset {asset_id}: {e}")
            
            print(f"✅ Deleted {len(bookyolo_asset_ids)} assets")
        
        # Step 4: Also check assets by notes/uri
        assets_result = supabase.table("assets").select("id, notes, uri").execute()
        
        additional_assets = []
        for asset in assets_result.data:
            notes = asset.get('notes', '') or ''
            uri = asset.get('uri', '') or ''
            
            if ('BookYolo' in notes or 'Specifications_Final' in notes or
                'BookYolo' in uri or 'Specifications_Final' in uri):
                if asset['id'] not in bookyolo_asset_ids:
                    additional_assets.append(asset['id'])
        
        if additional_assets:
            for asset_id in additional_assets:
                try:
                    supabase.table("assets").delete().eq("id", asset_id).execute()
                except Exception as e:
                    print(f"⚠️ Failed to delete asset {asset_id}: {e}")
            
            print(f"✅ Deleted {len(additional_assets)} additional assets")
        
        total_deleted = len(bookyolo_embeddings) + len(bookyolo_asset_ids) + len(additional_assets)
        print(f"\n✅ Cleanup complete! Removed {total_deleted} BookYolo-related records")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    print("🧹 Starting BookYolo document cleanup...")
    cleanup_bookyolo_documents()
    print("✨ Done!")

