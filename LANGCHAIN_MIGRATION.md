# LangChain Migration for Automatic LangSmith Tracing

## Overview

The RAG system has been migrated to use LangChain's built-in retrieval components, which provide **automatic LangSmith tracing** when `LANGSMITH_TRACING=true` is set. No manual `@traceable` decorators or `tracing_context` managers are needed.

## What Changed

### 1. Dependencies Added

```txt
langchain>=0.2.0
langchain-community>=0.2.0
langchain-openai>=0.1.0
```

### 2. New Files Created

- **`app/ai/langchain_retrievers.py`**: Custom LangChain retrievers that extend `BaseRetriever`
  - `SupabaseMessageRetriever`: Retrieves user messages from `message_embeddings` table
  - `SupabaseDocumentRetriever`: Retrieves document chunks from `document_embeddings` table
  - `SupabaseGlobalKnowledgeRetriever`: Retrieves global knowledge from `global_knowledge` table

### 3. Files Modified

- **`app/ai/rag_service.py`**: 
  - Now uses LangChain retrievers when available
  - Falls back to old implementation if LangChain not installed
  - Uses `OpenAIEmbeddings` from LangChain (automatically traced)

- **`requirements.txt`**: Added LangChain packages

## How It Works

### Automatic Tracing

When `LANGSMITH_TRACING=true` is set, LangChain automatically traces:
- **Retriever calls**: All `get_relevant_documents()` calls are traced
- **Embedding generation**: OpenAI embeddings are traced via LangChain's wrapper
- **Nested traces**: Traces automatically nest under parent traces

### Custom Retrievers

Our custom retrievers extend LangChain's `BaseRetriever` class:

```python
class SupabaseMessageRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        # This method is automatically traced by LangSmith
        # Calls Supabase RPC functions
        # Returns LangChain Documents
```

### Trace Structure in LangSmith

After migration, you should see:

```
chat_generation (parent trace)
├── get_rag_context
│   ├── SupabaseMessageRetriever (automatically traced)
│   ├── SupabaseDocumentRetriever (automatically traced)
│   └── SupabaseGlobalKnowledgeRetriever (automatically traced)
├── ChatOpenAI (LLM call)
│   └── internet_search (if web search is used)
```

## Environment Variables

Required for automatic tracing:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_api_key
LANGSMITH_PROJECT=simon-chatbot  # Optional
LANGSMITH_WORKSPACE_ID=your_workspace_id  # Optional (for org-scoped keys)
```

## Backward Compatibility

The system maintains backward compatibility:
- If LangChain is not installed, falls back to old implementation
- Old vector storage and document processor still work
- Gradual migration path available

## Benefits

1. **Automatic Tracing**: No manual decorators needed
2. **Standard Interface**: Uses LangChain's standard retriever interface
3. **Better Observability**: All retrieval operations automatically visible in LangSmith
4. **Future-Proof**: Easy to add more LangChain components (chains, agents, etc.)

## Testing

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export LANGSMITH_TRACING=true
   export LANGSMITH_API_KEY=your_key
   ```

3. **Test with a RAG query**:
   - "Who is my niche?"
   - "What documents do I have?"
   - Check LangSmith dashboard for nested traces

## Migration Notes

- **No database changes required**: Still uses existing Supabase tables and RPC functions
- **No API changes**: Same interface for calling RAG service
- **Performance**: Similar performance, with better observability
- **Error handling**: Same error handling, with better visibility

## Troubleshooting

### Traces Not Showing

1. Verify `LANGSMITH_TRACING=true` is set
2. Check `LANGSMITH_API_KEY` is valid
3. Ensure LangChain packages are installed
4. Check LangSmith dashboard project name matches `LANGSMITH_PROJECT`

### Import Errors

If you see import errors:
```bash
pip install langchain langchain-community langchain-openai
```

### Fallback to Old Implementation

If LangChain is not available, the system automatically falls back to the old implementation. Check logs for:
```
LANGCHAIN_AVAILABLE = False
```

## Next Steps

1. Deploy with LangChain dependencies
2. Set environment variables in Vercel
3. Test RAG queries and verify traces in LangSmith
4. Monitor performance and adjust retrieval parameters if needed

