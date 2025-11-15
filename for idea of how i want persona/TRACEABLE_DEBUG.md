# Debugging @traceable for Vector Retrieval

## Current Status

We're using `@traceable` decorator on async functions. If traces still don't show, here are potential issues:

## Potential Issues

### 1. Parent Trace Context Not Active

`@traceable` automatically nests within an active trace context. Ensure:
- `get_rag_context` is called **inside** the `chat_generation` trace
- The parent trace (`create_trace`) is active when retrieval functions are called

### 2. Async Context Propagation (Python <3.11)

In Python <3.11, async context propagation can be limited. Solutions:
- Upgrade to Python 3.11+
- Use explicit context passing (see below)

### 3. Environment Variables Not Set

Verify these are set **before** the decorator is applied:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=simon-chatbot
LANGSMITH_WORKSPACE_ID=your_workspace_id  # If using org-scoped key
```

## Alternative: Explicit Context Passing

If `@traceable` still doesn't work, we can use explicit RunTree passing:

```python
from langsmith import traceable, RunTree

@traceable
async def get_rag_context(..., run_tree: RunTree = None):
    with run_tree.child(name="VectorStoreRetriever_user_messages", run_type="retriever"):
        user_context = await self.vector_storage.get_similar_user_messages(...)
```

## Testing Steps

1. **Verify environment variables are loaded**:
   ```python
   import os
   print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
   print(f"LANGSMITH_API_KEY: {os.getenv('LANGSMITH_API_KEY')[:20]}...")
   ```

2. **Check if decorator is applied**:
   ```python
   print(f"Function: {vector_storage.get_similar_user_messages}")
   print(f"Has __wrapped__: {hasattr(vector_storage.get_similar_user_messages, '__wrapped__')}")
   ```

3. **Test with a simple RAG query**:
   - "Who is my niche?"
   - "What documents do I have?"
   - Check LangSmith dashboard for nested traces

## Next Steps if Still Not Working

1. **Consider LangChain Supabase Integration**:
   - Would require refactoring to use LangChain's Supabase vector store
   - Automatic tracing with `LANGSMITH_TRACING=true`
   - More standard approach, but significant code changes

2. **Use Manual RunTree Management**:
   - Explicitly create and pass RunTree objects
   - More control, but more verbose

3. **Check LangSmith SDK Version**:
   - Ensure `langsmith>=0.1.0` is installed
   - Some versions have better async support

