# @traceable Decorator Setup for Vector Retrieval

## Current Implementation

All vector retrieval functions now use the `@traceable` decorator:

1. **`VectorStoreRetriever_user_messages`** - in `vector_storage.py`
2. **`VectorStoreRetriever_global_knowledge`** - in `vector_storage.py`
3. **`VectorStoreRetriever_documents`** - in `document_processor.py`

## Required Environment Variables

The `@traceable` decorator requires these environment variables to be set:

```bash
LANGSMITH_API_KEY=your_api_key
LANGSMITH_PROJECT=simon-chatbot
LANGSMITH_WORKSPACE_ID=your_workspace_id  # If using org-scoped key
LANGSMITH_TRACING=true  # CRITICAL: Required for @traceable to work
LANGSMITH_TRACING_V2=true  # Also set this for v2 tracing
```

## How @traceable Works

The `@traceable` decorator:
- Automatically captures function inputs, outputs, and execution time
- **Automatically nests** when called within an existing trace context
- Uses `run_type="retriever"` to match LangSmith's expected format
- Reads configuration from environment variables

## Expected Trace Structure

When RAG is triggered, you should see:

```
chat_generation (parent trace)
├── get_rag_context
│   ├── VectorStoreRetriever_user_messages
│   ├── VectorStoreRetriever_global_knowledge
│   └── VectorStoreRetriever_documents
├── ChatOpenAI (LLM call)
│   └── internet_search (if web search is used)
```

## Troubleshooting

If vector retrievers still don't appear:

### 1. Verify Environment Variables

Check that `LANGSMITH_TRACING=true` is set:

```python
import os
print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
print(f"LANGSMITH_API_KEY: {os.getenv('LANGSMITH_API_KEY')[:20]}...")  # First 20 chars
```

### 2. Check Decorator Application

The decorators are applied at class definition time. Verify they're being applied:

```python
# Check if decorator is applied
from app.ai.vector_storage import vector_storage
print(vector_storage.get_similar_user_messages.__name__)
# Should show the function name, not a wrapper
```

### 3. Verify Trace Nesting

The `@traceable` decorator should automatically nest when called within an existing trace. Ensure:
- Parent trace (`chat_generation`) is active when RAG functions are called
- Environment variables are set before the decorator is applied
- `LANGSMITH_TRACING=true` is set (not just `LANGSMITH_TRACING_V2`)

### 4. Check LangSmith Dashboard

- Make sure you're looking at the correct project
- Check if filters are hiding nested traces
- Try expanding the parent trace to see nested children
- Look for traces with `run_type="retriever"`

### 5. Test with Simple Function

Test if `@traceable` is working at all:

```python
from langsmith import traceable

@traceable(run_type="tool", name="test_function")
def test_func(x):
    return x * 2

result = test_func(5)
# Check LangSmith dashboard for "test_function" trace
```

## Code Changes Made

1. **Added `LANGSMITH_TRACING=true`** to environment variables
2. **Added `project_name` parameter** to `@traceable` decorators
3. **Ensured environment variables are set** before decorator application
4. **Split functions** into public (decorated) and private (`_impl`) methods

## Next Steps

1. **Deploy the updated code**
2. **Verify environment variables** are set in production (Vercel)
3. **Test with a RAG question** (e.g., "Who is my niche?")
4. **Check LangSmith dashboard** for nested `VectorStoreRetriever` traces

## Important Notes

- `@traceable` reads from environment variables, not function parameters
- The decorator must be applied at class definition time
- Environment variables must be set before the module is imported
- `LANGSMITH_TRACING=true` is required (not just `LANGSMITH_TRACING_V2`)

