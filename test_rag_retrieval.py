"""
RAG Retrieval Testing Script
Tests RAG retrieval quality and relevance
"""

import requests
import json
from typing import List, Dict

BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000002"


def test_rag_retrieval(query: str, user_id: str = DEFAULT_USER_ID, project_id: str = DEFAULT_PROJECT_ID):
    """
    Test RAG retrieval by sending a query and checking if relevant context is retrieved
    
    Args:
        query: Test query to send
        user_id: User ID for RAG retrieval
        project_id: Project ID for RAG retrieval
    
    Returns:
        Retrieval results and analysis
    """
    print(f"\n{'='*60}")
    print(f"🔍 Testing RAG Retrieval")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"User ID: {user_id}")
    print(f"Project ID: {project_id}")
    print("-" * 60)
    
    # Send chat request to test RAG
    chat_url = f"{BACKEND_URL}/api/v1/chat"
    
    headers = {
        "X-User-ID": user_id,
        "X-Project-ID": project_id,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": query,
        "session_id": None,  # Will create new session
        "project_id": project_id
    }
    
    try:
        print("📤 Sending query...")
        response = requests.post(chat_url, headers=headers, json=payload, stream=True)
        
        if response.status_code == 200:
            # Collect streamed response
            full_response = ""
            print("\n📥 AI Response:")
            print("-" * 60)
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            if data.get('type') == 'content':
                                content = data.get('content', '')
                                print(content, end='', flush=True)
                                full_response += content
                            elif data.get('done'):
                                print("\n" + "-" * 60)
                                break
                        except json.JSONDecodeError:
                            continue
            
            # Analyze response
            print("\n📊 Analysis:")
            print("-" * 60)
            
            # Check if response seems relevant (basic heuristics)
            relevance_indicators = [
                "document", "pdf", "file", "according to", "based on",
                "mentioned", "in your", "from your", "you provided"
            ]
            
            has_references = any(indicator in full_response.lower() for indicator in relevance_indicators)
            
            print(f"✅ Response length: {len(full_response)} characters")
            print(f"{'✅' if has_references else '⚠️'} Contains reference indicators: {has_references}")
            
            if has_references:
                print("✅ Response appears to reference ingested documents")
            else:
                print("⚠️ Response may not be referencing ingested documents")
                print("   Check backend logs for RAG retrieval details")
            
            return {
                "success": True,
                "query": query,
                "response": full_response,
                "has_references": has_references,
                "response_length": len(full_response)
            }
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Error: {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def run_test_suite():
    """Run a suite of test queries"""
    test_queries = [
        "What did you learn from my documents?",
        "Summarize the key points from my PDFs",
        "What are the main strategies mentioned in my documents?",
        "What content guidelines do you have?",
        "Tell me about the hook formulas you know"
    ]
    
    print("\n" + "="*60)
    print("🧪 RAG Retrieval Test Suite")
    print("="*60)
    
    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}/{len(test_queries)}")
        result = test_rag_retrieval(query)
        results.append(result)
        print("\n" + "-"*60)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Suite Summary")
    print("="*60)
    
    successful = sum(1 for r in results if r.get('success'))
    with_references = sum(1 for r in results if r.get('has_references'))
    
    print(f"✅ Successful queries: {successful}/{len(test_queries)}")
    print(f"📚 Queries with document references: {with_references}/{len(test_queries)}")
    
    if with_references == len(test_queries):
        print("\n🎉 All tests show RAG is working correctly!")
    elif with_references > 0:
        print("\n⚠️ Some queries retrieved context, but not all")
        print("   Check backend logs for RAG retrieval details")
    else:
        print("\n❌ No queries retrieved context")
        print("   Check:")
        print("   1. Embeddings exist in database")
        print("   2. User ID matches between ingestion and chat")
        print("   3. Backend logs for RAG errors")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Single query test
        query = " ".join(sys.argv[1:])
        test_rag_retrieval(query)
    else:
        # Run test suite
        run_test_suite()

