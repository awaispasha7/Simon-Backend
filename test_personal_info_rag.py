#!/usr/bin/env python3
"""
Test script to verify personal info RAG retrieval
"""

import asyncio
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

async def test_personal_info_retrieval():
    """Test if personal info can be retrieved from RAG"""
    
    try:
        from app.ai.embedding_service import get_embedding_service
        from app.ai.vector_storage import vector_storage
        from app.database.supabase import get_supabase_client
        
        print("🧪 Testing Personal Info RAG Retrieval...")
        print("=" * 60)
        
        # Test 1: Check if personal info chunks exist in database
        print("\n📚 Test 1: Checking if personal info chunks exist...")
        supabase = get_supabase_client()
        
        # Search for chunks with "Personal_info" in tags or description
        result = supabase.table('global_knowledge').select('*').execute()
        
        personal_info_chunks = []
        for item in result.data:
            tags = item.get('tags', [])
            description = item.get('description', '')
            example_text = item.get('example_text', '')
            
            # Check if it's from Personal_info.txt
            if any('personal' in str(tag).lower() for tag in tags) or \
               'personal' in description.lower() or \
               'simon' in example_text.lower() or \
               'coaching' in example_text.lower() or \
               'liposuction' in example_text.lower():
                personal_info_chunks.append(item)
        
        print(f"✅ Found {len(personal_info_chunks)} personal info chunks in database")
        
        if personal_info_chunks:
            print("\n📋 Sample personal info chunks:")
            for i, chunk in enumerate(personal_info_chunks[:3], 1):
                print(f"\n  Chunk {i}:")
                print(f"    ID: {chunk.get('knowledge_id')}")
                print(f"    Category: {chunk.get('category')}")
                print(f"    Tags: {chunk.get('tags')}")
                print(f"    Quality Score: {chunk.get('quality_score')}")
                print(f"    Preview: {chunk.get('example_text', '')[:200]}...")
        else:
            print("❌ No personal info chunks found!")
            print("\n💡 The training might not have stored the chunks correctly.")
            print("   Try running: python train_rag.py rag-training-data/Personal_info.txt --type global")
            return
        
        # Test 2: Test similarity search with "do you know about me?"
        print("\n🔍 Test 2: Testing similarity search with 'do you know about me?'...")
        embedding_service = get_embedding_service()
        
        test_queries = [
            "do you know about me?",
            "tell me about myself",
            "what do you know about simon",
            "who am I",
            "coaching and health",
            "liposuction and weight loss"
        ]
        
        for query in test_queries:
            print(f"\n  Query: '{query}'")
            query_embedding = await embedding_service.generate_query_embedding(query)
            
            # Test with different thresholds
            for threshold in [0.05, 0.3, 0.5, 0.7]:
                results = await vector_storage.get_similar_global_knowledge(
                    query_embedding=query_embedding,
                    match_count=10,
                    similarity_threshold=threshold,
                    min_quality_score=0.6
                )
                
                # Check if any personal info chunks are in results
                personal_matches = []
                for result in results:
                    result_id = result.get('knowledge_id')
                    for chunk in personal_info_chunks:
                        if chunk.get('knowledge_id') == result_id:
                            personal_matches.append({
                                'similarity': result.get('similarity'),
                                'preview': result.get('example_text', '')[:150]
                            })
                            break
                
                if personal_matches:
                    print(f"    Threshold {threshold}: Found {len(personal_matches)} personal info matches")
                    for match in personal_matches[:2]:
                        print(f"      - Similarity: {match['similarity']:.3f}, Preview: {match['preview']}...")
                else:
                    print(f"    Threshold {threshold}: No personal info matches")
        
        # Test 3: Check all global knowledge items to see what's being retrieved
        print("\n📊 Test 3: Checking what global knowledge items are typically retrieved...")
        query_embedding = await embedding_service.generate_query_embedding("do you know about me?")
        results = await vector_storage.get_similar_global_knowledge(
            query_embedding=query_embedding,
            match_count=20,
            similarity_threshold=0.05,
            min_quality_score=0.6
        )
        
        print(f"\n  Retrieved {len(results)} items with threshold 0.05:")
        for i, item in enumerate(results[:5], 1):
            tags = item.get('tags', [])
            category = item.get('category', 'unknown')
            similarity = item.get('similarity', 0)
            preview = item.get('example_text', '')[:100]
            print(f"    {i}. [{category}] Similarity: {similarity:.3f}, Tags: {tags}")
            print(f"       Preview: {preview}...")
        
        # Test 4: Lower quality score threshold
        print("\n🔍 Test 4: Testing with lower quality score threshold...")
        results_low_quality = await vector_storage.get_similar_global_knowledge(
            query_embedding=query_embedding,
            match_count=20,
            similarity_threshold=0.05,
            min_quality_score=0.0  # No quality filter
        )
        
        personal_matches_low = []
        for result in results_low_quality:
            result_id = result.get('knowledge_id')
            for chunk in personal_info_chunks:
                if chunk.get('knowledge_id') == result_id:
                    personal_matches_low.append({
                        'similarity': result.get('similarity'),
                        'quality': chunk.get('quality_score'),
                        'preview': result.get('example_text', '')[:150]
                    })
                    break
        
        if personal_matches_low:
            print(f"  ✅ Found {len(personal_matches_low)} personal info matches with no quality filter:")
            for match in personal_matches_low[:3]:
                print(f"    - Similarity: {match['similarity']:.3f}, Quality: {match['quality']}, Preview: {match['preview']}...")
        else:
            print("  ❌ Still no personal info matches even with no quality filter")
        
        print("\n" + "=" * 60)
        print("✅ Testing complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_personal_info_retrieval())

