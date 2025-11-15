# LangSmith RAG Tracing Fix

## Problem

RAG operations (document retrieval, vector search, context building) were not appearing as nested traces within the main LLM trace in LangSmith. They appeared as separate top-level traces instead of being nested under the chat generation flow.

## Root Cause

The RAG context retrieval was happening **before** the LLM trace was created, so they appeared as separate traces:
1. RAG trace created (separate)
2. LLM trace created via `wrap_openai` (separate)

## Solution

Created a **parent trace** (`chat_generation`) that wraps the entire chat flow, including:
- RAG context retrieval
- LLM generation
- Response streaming

This ensures all operations appear nested under a single parent trace in LangSmith.

## Changes Made

### File: `Simon-Backend/app/api/simple_chat.py`

Added a parent trace wrapper around the entire `generate_stream()` function:

```python
# Parent trace wraps entire chat generation (RAG + LLM)
with create_trace(
    name="chat_generation",
    run_type="chain",
    tags=["chat", "rag", "llm"],
    metadata={
        "user_id": str(user_id) if user_id else None,
        "session_id": str(session_id) if session_id else None,
        "project_id": str(project_id) if project_id else None,
        "message_length": len(chat_request.text) if chat_request.text else 0,
        "enable_web_search": chat_request.enable_web_search or False
    }
):
    # RAG retrieval happens here (nested)
    # LLM generation happens here (nested)
    # Response streaming happens here (nested)
```

## Trace Hierarchy (Expected)

After this fix, LangSmith should show:

```
chat_generation (parent trace)
├── get_rag_context
│   ├── generate_query_embedding
│   ├── get_similar_user_messages
│   ├── get_similar_global_knowledge
│   └── get_document_context
├── ChatOpenAI (LLM call)
│   └── internet_search (if web search is used)
└── Response streaming
```

## How to Verify

1. **Check LangSmith Dashboard:**
   - Open a trace for a chat request
   - You should see `chat_generation` as the parent trace
   - RAG operations should be nested under it
   - LLM call should also be nested under it

2. **Look for these traces:**
   - `chat_generation` - Parent trace
   - `get_rag_context` - RAG context building
   - `embed_and_store_message` - Message embedding (if enabled)
   - `ChatOpenAI` - LLM call (automatic via wrap_openai)
   - `internet_search` - Web search (if used)

3. **Check Trace Metadata:**
   - Parent trace should have metadata: `user_id`, `session_id`, `message_length`, `enable_web_search`
   - RAG traces should have metadata: `user_id`, `project_id`, `user_message_length`, etc.

## Additional RAG Traces

The following RAG operations are already traced (they should now appear nested):

1. **`get_rag_context`** - Main RAG context retrieval
   - Tags: `["rag", "retrieval", "context_building"]`
   - Metadata: user_id, project_id, message length, conversation history

2. **`embed_and_store_message`** - Message embedding storage
   - Tags: `["rag", "embedding", "storage"]`
   - Metadata: message_id, user_id, project_id, session_id, role, content_length

3. **`extract_and_store_knowledge`** - Knowledge extraction
   - Tags: `["rag", "knowledge_extraction", "storage"]`
   - Metadata: user_id, project_id, conversation_length

4. **`process_document`** - Document processing (in document_processor.py)
   - Tags: `["document_processing", "embedding", "storage"]`
   - Metadata: asset_id, user_id, project_id, filename, content_type, file_size_bytes

5. **`generate_embedding`** - Embedding generation (in embedding_service.py)
   - Tags: `["embedding", "openai"]`
   - Metadata: text_length, model

## Troubleshooting

If RAG traces still don't appear nested:

1. **Check LangSmith Configuration:**
   ```python
   # Verify these are set in .env
   LANGSMITH_API_KEY=your_key
   LANGSMITH_PROJECT=simon-chatbot
   LANGSMITH_WORKSPACE_ID=your_workspace_id  # If using org-scoped key
   LANGSMITH_TRACING_V2=true
   ```

2. **Check Trace Creation:**
   - Verify `create_trace` is imported correctly
   - Check that `is_langsmith_enabled()` returns `True`
   - Look for any error messages in logs

3. **Verify Nesting:**
   - `tracing_context` should automatically nest when called within an existing trace
   - If traces are still separate, check that they're all within the parent `with create_trace()` block

4. **Check LangSmith Dashboard:**
   - Make sure you're looking at the correct project
   - Check if filters are hiding nested traces
   - Try expanding the parent trace to see nested children

## Expected Behavior

After this fix:
- ✅ All RAG operations appear nested under `chat_generation`
- ✅ LLM calls appear nested under `chat_generation`
- ✅ Web search calls appear nested under LLM calls
- ✅ Complete trace hierarchy visible in LangSmith dashboard
- ✅ All metadata properly attached to traces

## Next Steps

1. Test with a chat request that uses RAG
2. Check LangSmith dashboard for nested traces
3. Verify all RAG operations are visible
4. Check trace metadata is correct

