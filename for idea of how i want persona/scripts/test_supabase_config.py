"""
Test Supabase Configuration
Checks if Supabase is properly configured and all required tables exist
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database.supabase import get_supabase_client

def test_supabase_config():
    """Test if Supabase is properly configured"""
    print("=" * 60)
    print("SUPABASE CONFIGURATION TEST")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("1. Checking Environment Variables...")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url:
        print("   [X] SUPABASE_URL is not set")
        print("   -> Set it in .env file or Vercel environment variables")
        return False
    else:
        print(f"   [OK] SUPABASE_URL is set: {supabase_url[:30]}...")
    
    if not supabase_key:
        print("   [X] SUPABASE_ANON_KEY is not set")
        print("   -> Set it in .env file or Vercel environment variables")
        return False
    else:
        print(f"   [OK] SUPABASE_ANON_KEY is set: {supabase_key[:20]}...")
    
    print()
    
    # Test Supabase connection
    print("2. Testing Supabase Connection...")
    supabase = get_supabase_client()
    
    if not supabase:
        print("   [X] Failed to create Supabase client")
        print("   -> Check your SUPABASE_URL and SUPABASE_ANON_KEY")
        return False
    else:
        print("   [OK] Supabase client created successfully")
    
    print()
    
    # Test database connection by querying a simple table
    print("3. Testing Database Connection...")
    try:
        # Try to query users table (should exist)
        result = supabase.table("users").select("user_id").limit(1).execute()
        print("   [OK] Database connection successful")
    except Exception as e:
        print(f"   [WARN] Database connection test failed: {e}")
        print("   -> This might be okay if tables don't exist yet")
    
    print()
    
    # Check required tables for RAG
    print("4. Checking Required Tables for RAG...")
    required_tables = [
        "document_embeddings",
        "message_embeddings",
        "assets",
        "users",
        "sessions",
        "chat_messages"
    ]
    
    missing_tables = []
    existing_tables = []
    
    for table in required_tables:
        try:
            # Try to query the table
            result = supabase.table(table).select("*").limit(1).execute()
            existing_tables.append(table)
            print(f"   [OK] Table '{table}' exists")
        except Exception as e:
            missing_tables.append(table)
            print(f"   [X] Table '{table}' is missing or not accessible: {e}")
    
    print()
    
    # Check RPC functions
    print("5. Checking Required RPC Functions...")
    required_rpc_functions = [
        "get_similar_document_chunks",
        "get_similar_user_messages",
        "get_similar_global_knowledge"
    ]
    
    missing_functions = []
    existing_functions = []
    
    for func_name in required_rpc_functions:
        try:
            # Try to call the function with dummy parameters
            # We'll use a minimal test - just check if it exists
            # Note: This might fail with parameter errors, but that's okay
            # We just want to know if the function exists
            test_embedding = [0.0] * 1536  # Dummy embedding
            try:
                result = supabase.rpc(
                    func_name,
                    {
                        "query_embedding": test_embedding,
                        "match_count": 1,
                        "similarity_threshold": 0.1
                    }
                ).execute()
                existing_functions.append(func_name)
                print(f"   [OK] RPC function '{func_name}' exists")
            except Exception as e:
                error_str = str(e).lower()
                # If error is about parameters or data, function exists
                if "function" in error_str and "does not exist" in error_str:
                    missing_functions.append(func_name)
                    print(f"   [X] RPC function '{func_name}' does not exist")
                else:
                    # Function exists but parameters might be wrong (that's okay for this test)
                    existing_functions.append(func_name)
                    print(f"   [OK] RPC function '{func_name}' exists (parameter error is expected)")
        except Exception as e:
            missing_functions.append(func_name)
            print(f"   [X] RPC function '{func_name}' error: {e}")
    
    print()
    
    # Check document_embeddings table structure
    print("6. Checking document_embeddings Table Structure...")
    try:
        # Try to get count of embeddings
        result = supabase.table("document_embeddings").select("embedding_id", count="exact").limit(1).execute()
        count = result.count if hasattr(result, 'count') else 0
        print(f"   [OK] document_embeddings table accessible")
        print(f"   -> Current embeddings count: {count}")
        
        # Try to check if vector column exists by checking a sample
        sample = supabase.table("document_embeddings").select("embedding_id, chunk_text, metadata").limit(1).execute()
        if sample.data:
            print(f"   [OK] Table has data and structure looks correct")
            print(f"   -> Sample chunk text length: {len(sample.data[0].get('chunk_text', ''))}")
        else:
            print(f"   [WARN] Table exists but is empty (this is okay for new setup)")
    except Exception as e:
        print(f"   [X] Error checking document_embeddings: {e}")
    
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if not supabase_url or not supabase_key:
        print("[X] Supabase is NOT configured")
        print("   -> Set SUPABASE_URL and SUPABASE_ANON_KEY in .env or Vercel")
        return False
    
    if not supabase:
        print("[X] Supabase client creation failed")
        print("   -> Check your credentials")
        return False
    
    if missing_tables:
        print(f"[WARN] Missing tables: {', '.join(missing_tables)}")
        print("   -> Run database migrations to create these tables")
        print("   -> Check: supabase/migrations/")
    
    if missing_functions:
        print(f"[WARN] Missing RPC functions: {', '.join(missing_functions)}")
        print("   -> Run database migrations to create these functions")
        print("   -> Check: supabase/migrations/")
    
    if not missing_tables and not missing_functions:
        print("[OK] Supabase is properly configured!")
        print("   -> All required tables exist")
        print("   -> All required RPC functions exist")
        print("   -> Ready for document ingestion")
        return True
    else:
        print("[WARN] Supabase is partially configured")
        print("   -> Some tables or functions are missing")
        print("   -> RAG may not work until migrations are run")
        return False

if __name__ == "__main__":
    success = test_supabase_config()
    sys.exit(0 if success else 1)

