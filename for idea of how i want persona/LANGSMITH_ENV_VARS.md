# LangSmith Environment Variables

## Required for @traceable Decorator

The `@traceable` decorator only needs these two environment variables:

```bash
LANGSMITH_TRACING=true    # Enables tracing (REQUIRED)
LANGSMITH_API_KEY=your_key # Your API key (REQUIRED)
```

## Optional Variables

```bash
LANGSMITH_PROJECT=simon-chatbot  # Custom project name (defaults to "default")
LANGSMITH_WORKSPACE_ID=your_workspace_id  # Only needed for multi-workspace API keys
LANGSMITH_ENDPOINT=...  # Only for self-hosted or EU region
```

## Important Notes

- **`LANGSMITH_TRACING_V2` is deprecated** - Do NOT use it
- **Use `LANGSMITH_TRACING=true`** instead
- The `@traceable` decorator automatically reads from environment variables
- No need to pass `project_name` to the decorator if `LANGSMITH_PROJECT` is set in environment

## Setup for Vercel

In your Vercel project settings, add these environment variables:

1. **Required:**
   - `LANGSMITH_TRACING` = `true`
   - `LANGSMITH_API_KEY` = `your_api_key_here`

2. **Optional (but recommended):**
   - `LANGSMITH_PROJECT` = `simon-chatbot`
   - `LANGSMITH_WORKSPACE_ID` = `your_workspace_id` (if using org-scoped key)

## Verification

After setting environment variables, the `@traceable` decorator will:
- Automatically capture function inputs, outputs, and timing
- Automatically nest within existing trace contexts
- Appear in LangSmith dashboard with `run_type="retriever"`

## Current Implementation

All vector retrieval functions use `@traceable`:

- `VectorStoreRetriever_user_messages` - User message retrieval
- `VectorStoreRetriever_global_knowledge` - Global knowledge retrieval  
- `VectorStoreRetriever_documents` - Document chunk retrieval

These will automatically appear as nested traces under `get_rag_context` when RAG is triggered.

