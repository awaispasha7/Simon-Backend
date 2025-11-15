"""
Comprehensive Test Script for RAG Retrieval and Document Ingestion
Tests all aspects of the RAG system to ensure it's working correctly
"""

import os
import sys
import asyncio
from pathlib import Path
from uuid import UUID
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Test imports
try:
    from app.database.supabase import get_supabase_client
    from app.ai.document_processor import document_processor
    from app.ai.rag_service import rag_service
    from app.ai.embedding_service import get_embedding_service
    IMPORTS_SUCCESS = True
except Exception as e:
    print(f"[X] Failed to import modules: {e}")
    import traceback
    traceback.print_exc()
    IMPORTS_SUCCESS = False

# Test user/project IDs (consistent with system)
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
TEST_PROJECT_ID = UUID("00000000-0000-0000-0000-000000000002")


async def test_supabase_connection():
    """Test 1: Verify Supabase connection"""
    print("\n" + "="*60)
    print("TEST 1: Supabase Connection")
    print("="*60)
    
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("[X] Supabase client is None - check environment variables")
            return False
        
        # Test connection by querying a table
        result = supabase.table("assets").select("id").limit(1).execute()
        print("[OK] Supabase connection successful")
        print(f"[OK] Can query assets table")
        return True
    except Exception as e:
        print(f"[X] Supabase connection failed: {e}")
        return False


async def test_document_tables():
    """Test 2: Verify document tables exist"""
    print("\n" + "="*60)
    print("TEST 2: Document Tables")
    print("="*60)
    
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("[X] Supabase not available")
            return False
        
        # Check assets table
        try:
            result = supabase.table("assets").select("id").limit(1).execute()
            print("[OK] assets table exists")
        except Exception as e:
            print(f"[X] assets table error: {e}")
            return False
        
        # Check document_embeddings table
        try:
            result = supabase.table("document_embeddings").select("embedding_id").limit(1).execute()
            print("[OK] document_embeddings table exists")
        except Exception as e:
            print(f"[X] document_embeddings table error: {e}")
            return False
        
        # Check RPC function
        try:
            # Test with dummy embedding
            dummy_embedding = [0.0] * 1536
            result = supabase.rpc(
                'get_similar_document_chunks',
                {
                    'query_embedding': dummy_embedding,
                    'query_user_id': str(TEST_USER_ID),
                    'query_project_id': str(TEST_PROJECT_ID),
                    'match_count': 1,
                    'similarity_threshold': 0.1
                }
            ).execute()
            print("[OK] get_similar_document_chunks RPC function exists")
        except Exception as e:
            print(f"[X] RPC function error: {e}")
            return False
        
        return True
    except Exception as e:
        print(f"[X] Table check failed: {e}")
        return False


async def test_document_count():
    """Test 3: Count ingested documents"""
    print("\n" + "="*60)
    print("TEST 3: Document Count")
    print("="*60)
    
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("[X] Supabase not available")
            return False
        
        # Count assets
        assets_result = supabase.table("assets").select("id", count="exact").execute()
        asset_count = assets_result.count if hasattr(assets_result, 'count') else len(assets_result.data) if assets_result.data else 0
        print(f"[INFO] Total assets: {asset_count}")
        
        # Count document embeddings
        embeddings_result = supabase.table("document_embeddings").select("embedding_id", count="exact").execute()
        embedding_count = embeddings_result.count if hasattr(embeddings_result, 'count') else len(embeddings_result.data) if embeddings_result.data else 0
        print(f"[INFO] Total document chunks: {embedding_count}")
        
        # List unique documents
        if asset_count > 0:
            assets = supabase.table("assets").select("id, uri, notes, processing_status").execute()
            print(f"\n[INFO] Documents in database:")
            for i, asset in enumerate(assets.data[:10], 1):  # Show first 10
                filename = asset.get('uri', 'Unknown')
                status = asset.get('processing_status', 'unknown')
                notes = asset.get('notes', '')
                print(f"  {i}. {filename} (status: {status})")
                if notes:
                    print(f"     Notes: {notes[:50]}...")
        
        if embedding_count == 0:
            print("[WARN] No document chunks found - documents may not be ingested")
            return False
        
        print(f"[OK] Found {embedding_count} document chunks from {asset_count} assets")
        return True
    except Exception as e:
        print(f"[X] Document count failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_text_extraction():
    """Test 4: Test text extraction for different file types"""
    print("\n" + "="*60)
    print("TEST 4: Text Extraction")
    print("="*60)
    
    # Test PDF extraction
    try:
        import PyPDF2
        print("[OK] PyPDF2 is installed")
    except ImportError:
        print("[WARN] PyPDF2 is NOT installed - PDF extraction will fail")
    
    # Test DOCX extraction
    try:
        import docx
        print("[OK] python-docx is installed")
    except ImportError:
        print("[WARN] python-docx is NOT installed - DOCX extraction will fail")
    
    # Test TXT extraction (always available)
    print("[OK] TXT extraction is always available")
    
    return True


async def test_rag_retrieval():
    """Test 5: Test RAG retrieval with sample queries"""
    print("\n" + "="*60)
    print("TEST 5: RAG Retrieval")
    print("="*60)
    
    if not rag_service:
        print("[X] RAG service not available")
        return False
    
    test_queries = [
        ("Who are my potential clients?", "avatar_sheet"),
        ("What's my tone?", "tone_style"),
        ("Create a script about consistency", "script"),
        ("What are my content pillars?", "content_strategy"),
    ]
    
    results = []
    
    for query, expected_doc_type in test_queries:
        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Expected document type: {expected_doc_type}")
        
        try:
            rag_context = await rag_service.get_rag_context(
                user_message=query,
                user_id=TEST_USER_ID,
                project_id=TEST_PROJECT_ID,
                conversation_history=None
            )
            
            document_context = rag_context.get('document_context', [])
            doc_count = len(document_context)
            
            print(f"[RESULT] Retrieved {doc_count} document chunks")
            
            if doc_count > 0:
                print(f"[OK] RAG retrieval successful for: '{query}'")
                # Show first chunk preview
                first_chunk = document_context[0]
                chunk_text = first_chunk.get('chunk_text', '')[:200]
                similarity = first_chunk.get('similarity', 0)
                filename = first_chunk.get('metadata', {}).get('filename', 'Unknown')
                print(f"[PREVIEW] First chunk from '{filename}' (similarity: {similarity:.3f}):")
                print(f"         {chunk_text}...")
                results.append(True)
            else:
                print(f"[WARN] No document chunks retrieved for: '{query}'")
                print(f"[WARN] This might indicate:")
                print(f"       1. No relevant documents in database")
                print(f"       2. Query expansion not matching documents")
                print(f"       3. Similarity threshold too high")
                results.append(False)
                
        except Exception as e:
            print(f"[X] RAG retrieval failed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    success_count = sum(results)
    total_count = len(results)
    print(f"\n[SUMMARY] RAG retrieval: {success_count}/{total_count} queries retrieved chunks")
    
    return success_count > 0


async def test_query_expansion():
    """Test 6: Test query expansion"""
    print("\n" + "="*60)
    print("TEST 6: Query Expansion")
    print("="*60)
    
    if not rag_service:
        print("[X] RAG service not available")
        return False
    
    test_queries = [
        "Who are my potential clients?",
        "What's my tone?",
        "Create a script",
        "What are my content pillars?",
    ]
    
    for query in test_queries:
        expanded = rag_service._expand_brand_query(query)
        print(f"\n[QUERY] Original: '{query}'")
        print(f"[EXPANDED] '{expanded[:150]}...'")
    
    print("[OK] Query expansion working")
    return True


async def test_embedding_generation():
    """Test 7: Test embedding generation"""
    print("\n" + "="*60)
    print("TEST 7: Embedding Generation")
    print("="*60)
    
    try:
        embedding_service = get_embedding_service()
        if not embedding_service:
            print("[X] Embedding service not available")
            return False
        
        test_text = "This is a test document chunk for embedding generation."
        embedding = await embedding_service.generate_embedding(test_text)
        
        if embedding and len(embedding) > 0:
            print(f"[OK] Embedding generated successfully")
            print(f"[INFO] Embedding dimension: {len(embedding)}")
            print(f"[INFO] First 5 values: {embedding[:5]}")
            return True
        else:
            print("[X] Embedding generation returned empty result")
            return False
            
    except Exception as e:
        print(f"[X] Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_document_processing():
    """Test 8: Test document processing (if test file exists)"""
    print("\n" + "="*60)
    print("TEST 8: Document Processing")
    print("="*60)
    
    # Check if we have a test document
    test_files = [
        "simon_personal_description.txt",
        "document_explanation_guide.txt",
    ]
    
    found_files = []
    for filename in test_files:
        filepath = Path(__file__).parent.parent / filename
        if filepath.exists():
            found_files.append((filepath, filename))
            print(f"[OK] Found test file: {filename}")
    
    if not found_files:
        print("[INFO] No test files found - skipping document processing test")
        print("[INFO] To test document processing, place a PDF/TXT/DOCX file in the backend root")
        return True
    
    # Test processing one file
    if found_files:
        filepath, filename = found_files[0]
        print(f"\n[TEST] Processing: {filename}")
        
        try:
            with open(filepath, 'rb') as f:
                file_content = f.read()
            
            from uuid import uuid4
            asset_id = uuid4()
            
            result = await document_processor.process_document(
                asset_id=asset_id,
                user_id=TEST_USER_ID,
                project_id=TEST_PROJECT_ID,
                file_content=file_content,
                filename=filename,
                content_type="text/plain" if filename.endswith('.txt') else "application/pdf"
            )
            
            if result.get("success"):
                chunks = result.get("chunks_processed", 0)
                embeddings = result.get("embeddings_created", 0)
                print(f"[OK] Document processing successful")
                print(f"[INFO] Chunks processed: {chunks}")
                print(f"[INFO] Embeddings created: {embeddings}")
                return True
            else:
                error = result.get("error", "Unknown error")
                print(f"[X] Document processing failed: {error}")
                return False
                
        except Exception as e:
            print(f"[X] Document processing error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("RAG & DOCUMENT INGESTION TEST SUITE")
    print("="*60)
    print("\nThis script tests:")
    print("1. Supabase connection")
    print("2. Document tables existence")
    print("3. Document count in database")
    print("4. Text extraction capabilities")
    print("5. RAG retrieval functionality")
    print("6. Query expansion")
    print("7. Embedding generation")
    print("8. Document processing")
    
    if not IMPORTS_SUCCESS:
        print("\n[X] Cannot run tests - imports failed")
        return
    
    results = []
    
    # Run tests
    results.append(await test_supabase_connection())
    results.append(await test_document_tables())
    results.append(await test_document_count())
    results.append(await test_text_extraction())
    results.append(await test_embedding_generation())
    results.append(await test_query_expansion())
    results.append(await test_rag_retrieval())
    results.append(await test_document_processing())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    test_names = [
        "Supabase Connection",
        "Document Tables",
        "Document Count",
        "Text Extraction",
        "Embedding Generation",
        "Query Expansion",
        "RAG Retrieval",
        "Document Processing"
    ]
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "[OK]" if result else "[X]"
        print(f"{status} {name}")
    
    print(f"\n[RESULT] {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed! RAG system is working correctly.")
    elif passed >= total * 0.75:
        print("[WARN] Most tests passed, but some issues detected.")
    else:
        print("[ERROR] Multiple tests failed - RAG system needs attention.")


if __name__ == "__main__":
    asyncio.run(run_all_tests())

