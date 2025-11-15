# Vercel Deployment Size Fix

## Problem

Vercel deployment failed with error:
```
Error: A Serverless Function has exceeded the unzipped maximum size of 250 MB.
```

## Root Cause

LangChain packages (`langchain`, `langchain-community`, `langchain-openai`) are too large for Vercel's 250 MB serverless function limit.

## Solution

Removed LangChain dependencies and reverted to manual tracing with `@traceable` decorators.

### Changes Made

1. **Removed LangChain packages** from `requirements.txt`:
   - Removed: `langchain>=0.2.0`
   - Removed: `langchain-community>=0.2.0`
   - Removed: `langchain-openai>=0.1.0`

2. **Reverted RAG service** to use manual tracing:
   - Uses `@traceable` decorators on retrieval functions
   - Functions in `vector_storage.py` and `document_processor.py` already have `@traceable`

3. **Kept LangSmith integration**:
   - `langsmith>=0.1.0` remains (lightweight)
   - `@traceable` decorators work without LangChain

## Current Tracing Setup

All retrieval functions use `@traceable` decorators:

- `VectorStoreRetriever_user_messages` - in `vector_storage.py`
- `VectorStoreRetriever_global_knowledge` - in `vector_storage.py`
- `VectorStoreRetriever_documents` - in `document_processor.py`

These are automatically traced when:
- `LANGSMITH_TRACING=true` is set
- `LANGSMITH_API_KEY` is set
- Functions are called within the `get_rag_context` trace context

## Expected Trace Structure

```
chat_generation (parent trace)
├── get_rag_context
│   ├── VectorStoreRetriever_user_messages
│   ├── VectorStoreRetriever_global_knowledge
│   └── VectorStoreRetriever_documents
└── ChatOpenAI
```

## Next Steps

1. **Deploy** - Should now fit within Vercel's 250 MB limit
2. **Test** - Make a RAG query and check LangSmith dashboard
3. **Verify** - Ensure traces appear nested correctly

## If Traces Still Don't Show

1. Check environment variables are set in Vercel
2. Verify `@traceable` decorators are applied (they are)
3. Check logs for any errors
4. Ensure parent trace (`get_rag_context`) is active when retrievers are called

