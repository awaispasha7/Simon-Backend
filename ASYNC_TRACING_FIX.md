# Fix: Vector Retrieval Traces Not Showing in LangSmith

## Problem

Vector retrieval traces (`VectorStoreRetriever_user_messages`, `VectorStoreRetriever_global_knowledge`, `VectorStoreRetriever_documents`) were not appearing in LangSmith, even though:
- `@traceable` decorators were applied
- Environment variables were set correctly
- RAG was working (retrieving context successfully)

Only `ChatOpenAI` traces were visible.

## Root Cause

**We're NOT using LangChain** - we're using custom Supabase RPC functions for vector search.

The `@traceable` decorator has **async context propagation issues** in Python, especially when:
- Functions are async
- Functions are called within async contexts
- Context needs to be propagated across async boundaries

## Solution

Replaced `@traceable` decorator with **`tracing_context` context managers** inside the async functions.

### Why `tracing_context` Works Better for Async

1. **Explicit Context Management**: Context managers explicitly handle async context propagation
2. **Proper Nesting**: Ensures traces nest correctly within parent traces
3. **Async-Safe**: Designed to work with Python's async/await model

### Changes Made

#### `vector_storage.py`

**Before:**
```python
@traceable(run_type="retriever", name="VectorStoreRetriever_user_messages")
async def get_similar_user_messages(...):
    return await self._get_similar_user_messages_impl(...)
```

**After:**
```python
async def get_similar_user_messages(...):
    if LANGSMITH_AVAILABLE and tracing_context:
        with tracing_context(
            project_name=LANGSMITH_PROJECT,
            name="VectorStoreRetriever_user_messages",
            run_type="retriever",
            tags=["rag", "vector_search", "retrieval"],
            metadata={...}
        ):
            return await self._get_similar_user_messages_impl(...)
    else:
        return await self._get_similar_user_messages_impl(...)
```

#### `document_processor.py`

Same pattern applied to `get_document_context`.

## Required Environment Variables

```bash
LANGSMITH_TRACING=true    # REQUIRED
LANGSMITH_API_KEY=your_key # REQUIRED
LANGSMITH_PROJECT=simon-chatbot  # Optional (defaults to "default")
LANGSMITH_WORKSPACE_ID=your_workspace_id  # Optional (only for multi-workspace keys)
```

## Expected Trace Structure

After this fix, LangSmith should show:

```
chat_generation (parent trace)
├── get_rag_context
│   ├── VectorStoreRetriever_user_messages
│   ├── VectorStoreRetriever_global_knowledge
│   └── VectorStoreRetriever_documents
├── ChatOpenAI (LLM call)
│   └── internet_search (if web search is used)
```

## Verification

1. **Set environment variables** in Vercel:
   - `LANGSMITH_TRACING` = `true`
   - `LANGSMITH_API_KEY` = your key
   - `LANGSMITH_PROJECT` = `simon-chatbot` (optional)
   - `LANGSMITH_WORKSPACE_ID` = your workspace ID (if using org-scoped key)

2. **Deploy and test**:
   - Ask a RAG question like "Who is my niche?" or "What documents do I have?"
   - Check LangSmith dashboard
   - You should see `VectorStoreRetriever` traces nested under `get_rag_context`

## Key Differences: @traceable vs tracing_context

| Feature | @traceable | tracing_context |
|---------|-----------|-----------------|
| Async Support | Can have context issues | Explicit async support |
| Context Propagation | Automatic (may fail) | Explicit (guaranteed) |
| Nesting | Automatic (may fail) | Explicit (guaranteed) |
| Use Case | Simple sync functions | Async functions, complex flows |

## Notes

- We're **NOT using LangChain** - we use custom Supabase RPC functions
- LangChain's built-in retrievers would trace automatically, but we need manual tracing
- `tracing_context` is the recommended approach for async functions in LangSmith

