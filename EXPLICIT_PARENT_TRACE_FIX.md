# Fix: Explicit Parent Run Tree for Async Context Propagation

## Problem

Vector retrieval traces were not appearing in LangSmith due to **async context propagation issues**. When using `tracing_context` with async functions, the parent trace context wasn't being properly propagated to child traces.

## Root Cause

- **Python <3.11**: Limited async context propagation support
- **tracing_context with async**: Context may not propagate correctly through async/await boundaries
- **Missing parent link**: Child traces weren't explicitly linked to parent traces

## Solution

**Explicitly pass parent run tree** to child functions using `get_current_run_tree()` from LangSmith.

### Changes Made

#### 1. **RAG Service** (`rag_service.py`)

- Get current run tree inside `get_rag_context` trace
- Pass it explicitly to all retrieval functions

```python
# Get current run tree for this trace to pass to child functions
try:
    from langsmith import get_current_run_tree
    rag_run_tree = get_current_run_tree()
except (ImportError, Exception):
    rag_run_tree = None

# Pass to child functions
user_context = await self.vector_storage.get_similar_user_messages(
    ...,
    parent_run_tree=rag_run_tree
)
```

#### 2. **Vector Storage** (`vector_storage.py`)

- Added `parent_run_tree` parameter to retrieval functions
- Pass parent to `tracing_context` if provided

```python
async def get_similar_user_messages(
    ...,
    parent_run_tree: Optional[Any] = None
):
    trace_kwargs = {...}
    if parent_run_tree is not None:
        trace_kwargs["parent"] = parent_run_tree
    
    with tracing_context(**trace_kwargs):
        return await self._get_similar_user_messages_impl(...)
```

#### 3. **Document Processor** (`document_processor.py`)

- Same pattern: accept `parent_run_tree` and pass to `tracing_context`

## How It Works

1. **Parent Trace**: `get_rag_context` creates a trace and gets its run tree
2. **Explicit Passing**: Run tree is passed as parameter to child functions
3. **Child Traces**: Child functions use the parent run tree in `tracing_context`
4. **Proper Nesting**: Traces now properly nest in LangSmith

## Expected Trace Structure

```
chat_generation (parent trace)
├── get_rag_context
│   ├── VectorStoreRetriever_user_messages (explicitly linked)
│   ├── VectorStoreRetriever_global_knowledge (explicitly linked)
│   └── VectorStoreRetriever_documents (explicitly linked)
└── ChatOpenAI
```

## Benefits

1. **Works with Python <3.11**: Explicit passing doesn't rely on async context vars
2. **Reliable Nesting**: Parent-child relationship is explicit
3. **No Context Loss**: Context is preserved across async boundaries
4. **Backward Compatible**: Functions still work if parent_run_tree is None

## Testing

1. **Deploy** the changes
2. **Test with RAG query**: "Who is my niche?" or "tell me about hooks"
3. **Check LangSmith**: Vector retrieval traces should appear nested under `get_rag_context`

## Alternative Solutions (If This Doesn't Work)

1. **Upgrade to Python 3.11+**: Better async context propagation
2. **Use @traceable decorator**: May handle async better in newer LangSmith versions
3. **Synchronous wrappers**: Convert async functions to sync for tracing

