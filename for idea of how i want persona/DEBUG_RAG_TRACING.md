# Debug: RAG Traces Not Showing in LangSmith

## Current Status

RAG traces are still not appearing in LangSmith dashboard. Only `ChatOpenAI` traces are visible.

## Debugging Steps

### 1. Check if LangChain is Installed

Add this to your logs or check deployment:

```python
try:
    import langchain
    print(f"[DEBUG] LangChain version: {langchain.__version__}")
    print(f"[DEBUG] LANGCHAIN_AVAILABLE: True")
except ImportError as e:
    print(f"[DEBUG] LangChain not installed: {e}")
    print(f"[DEBUG] LANGCHAIN_AVAILABLE: False")
```

### 2. Check Environment Variables

Verify these are set in your deployment:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=simon-chatbot
```

### 3. Check Logs for RAG Activity

Look for these log messages:

```
[RAG] Using LangChain retrievers (LANGCHAIN_AVAILABLE=True)
[RAG] Retrieving user messages...
[RAG] SupabaseMessageRetriever: Generating embedding...
```

If you see `LANGCHAIN_AVAILABLE=False`, LangChain is not installed.

### 4. Verify Retriever Calls

The retrievers should be called via:
- `retriever.invoke(query)` - Preferred (ensures proper tracing)
- `retriever.get_relevant_documents(query)` - Fallback

### 5. Check LangSmith Dashboard

1. Go to LangSmith dashboard
2. Filter by project: `simon-chatbot`
3. Look for traces with:
   - `SupabaseMessageRetriever`
   - `SupabaseDocumentRetriever`
   - `SupabaseGlobalKnowledgeRetriever`

## Potential Issues

### Issue 1: LangChain Not Installed

**Symptom**: Logs show `LANGCHAIN_AVAILABLE=False`

**Solution**: Install LangChain packages:
```bash
pip install langchain langchain-community langchain-openai
```

### Issue 2: Environment Variables Not Set

**Symptom**: No traces at all in LangSmith

**Solution**: Set in Vercel:
- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY=your_key`

### Issue 3: Retrievers Not Being Called

**Symptom**: No RAG logs in console

**Solution**: Check if RAG is actually being triggered. Add test query:
- "Who is my niche?"
- "What documents do I have?"

### Issue 4: Traces Not Nesting

**Symptom**: Traces appear but not nested under `get_rag_context`

**Solution**: Ensure parent trace is active when retrievers are called.

## Quick Test

Add this test endpoint to verify tracing:

```python
@router.get("/test-rag-tracing")
async def test_rag_tracing():
    """Test endpoint to verify RAG tracing"""
    try:
        from app.ai.langchain_retrievers import SupabaseMessageRetriever
        from uuid import UUID
        
        retriever = SupabaseMessageRetriever(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            k=5
        )
        
        docs = retriever.invoke("test query")
        return {
            "status": "success",
            "docs_count": len(docs),
            "langchain_available": True
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "langchain_available": False
        }
```

## Next Steps

1. **Check deployment logs** for `[RAG]` messages
2. **Verify LangChain is installed** in production
3. **Test with explicit RAG query** like "Who is my niche?"
4. **Check LangSmith dashboard** after making a query
5. **Review error logs** for any import or runtime errors

