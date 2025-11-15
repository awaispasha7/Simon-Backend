# Current LangSmith Tracking System

## Overview

The system uses **LangSmith** for observability and tracing of all AI operations. Tracking is implemented using a combination of automatic tracing (for OpenAI) and manual tracing (for custom operations).

## Architecture

### 1. **Parent Trace Structure**

```
chat_generation (top-level trace)
├── get_rag_context (RAG operations)
│   ├── VectorStoreRetriever_user_messages
│   ├── VectorStoreRetriever_global_knowledge
│   └── VectorStoreRetriever_documents
├── ChatOpenAI (LLM calls - automatic)
│   └── internet_search (if web search enabled)
└── Response streaming
```

### 2. **Tracing Methods**

#### **Automatic Tracing (OpenAI)**
- **Location**: `app/ai/langsmith_config.py`
- **Method**: `wrap_openai_client()`
- **What it traces**:
  - All OpenAI chat completions
  - All OpenAI embeddings
  - Token usage, latency, model info
- **Implementation**: Uses LangSmith's `wrap_openai()` to automatically wrap OpenAI clients

#### **Manual Tracing (RAG & Custom Operations)**
- **Location**: `app/ai/langsmith_config.py`
- **Method**: `create_trace()` - returns `tracing_context` context manager
- **What it traces**:
  - RAG context building (`get_rag_context`)
  - Vector retrieval operations
  - Document processing
- **Implementation**: Uses `tracing_context` from `langsmith.run_helpers`

### 3. **Vector Retrieval Tracing**

All vector retrieval functions use **`tracing_context`** context managers (not `@traceable` decorators) because:
- More reliable with async functions
- Better context propagation
- Explicit control over trace nesting

**Traced Functions**:
1. **`VectorStoreRetriever_user_messages`** (`vector_storage.py`)
   - Retrieves similar user messages from `message_embeddings` table
   - Uses `tracing_context` with `run_type="retriever"`

2. **`VectorStoreRetriever_global_knowledge`** (`vector_storage.py`)
   - Retrieves global knowledge patterns from `global_knowledge` table
   - Uses `tracing_context` with `run_type="retriever"`

3. **`VectorStoreRetriever_documents`** (`document_processor.py`)
   - Retrieves document chunks from `document_embeddings` table
   - Uses `tracing_context` with `run_type="retriever"`

### 4. **Trace Hierarchy**

**Top Level**: `chat_generation`
- Wraps entire chat flow
- Created in: `app/api/simple_chat.py` → `generate_stream()`
- Metadata: user_id, session_id, project_id, message_length, enable_web_search

**RAG Level**: `get_rag_context`
- Wraps all RAG operations
- Created in: `app/ai/rag_service.py` → `get_rag_context()`
- Metadata: user_id, project_id, message_length, conversation_history

**Retrieval Level**: Individual retrievers
- Created inside each retrieval function
- Uses `tracing_context` context manager
- Automatically nests under `get_rag_context`

## Environment Variables

### Required
```bash
LANGSMITH_TRACING=true    # Enables tracing
LANGSMITH_API_KEY=your_key # Your API key
```

### Optional
```bash
LANGSMITH_PROJECT=simon-chatbot  # Project name (defaults to "default")
LANGSMITH_WORKSPACE_ID=your_workspace_id  # Only for org-scoped API keys
```

## Files Involved

### Core Configuration
- **`app/ai/langsmith_config.py`**
  - Central LangSmith configuration
  - `wrap_openai_client()` - Automatic OpenAI tracing
  - `create_trace()` - Manual trace creation
  - `is_langsmith_enabled()` - Check if tracing is available

### Vector Storage
- **`app/ai/vector_storage.py`**
  - `get_similar_user_messages()` - Traced with `tracing_context`
  - `get_similar_global_knowledge()` - Traced with `tracing_context`

### Document Processing
- **`app/ai/document_processor.py`**
  - `get_document_context()` - Traced with `tracing_context`

### RAG Service
- **`app/ai/rag_service.py`**
  - `get_rag_context()` - Wrapped with `create_trace()`
  - Orchestrates all retrieval operations

### Chat API
- **`app/api/simple_chat.py`**
  - `generate_stream()` - Wrapped with `create_trace("chat_generation")`
  - Top-level trace for entire chat flow

### AI Models
- **`app/ai/models.py`**
  - OpenAI client wrapped with `wrap_openai_client()`
  - Automatic tracing for all LLM calls

### Embedding Service
- **`app/ai/embedding_service.py`**
  - OpenAI embeddings client wrapped with `wrap_openai_client()`
  - Automatic tracing for embedding generation

## Current Status

### ✅ Working
- OpenAI chat completions (automatic tracing)
- OpenAI embeddings (automatic tracing)
- Parent trace structure (`chat_generation`, `get_rag_context`)

### ⚠️ Issue
- Vector retrieval traces not appearing in LangSmith dashboard
- Even though RAG is working (logs show retrieval happening)
- Traces should appear but don't show up in UI

## Why Traces Might Not Show

1. **Async Context Propagation**: `tracing_context` might not be propagating correctly in async functions
2. **Parent Trace Not Active**: Retrievers might be called outside the parent trace context
3. **Environment Variables**: Not set correctly in production
4. **LangSmith SDK Version**: Compatibility issues with async tracing

## Next Steps to Debug

1. **Verify environment variables** are set in production
2. **Check logs** for any LangSmith errors
3. **Test with synchronous calls** to see if async is the issue
4. **Verify parent trace** is active when retrievers are called
5. **Check LangSmith dashboard** project name matches `LANGSMITH_PROJECT`

## Dependencies

```txt
langsmith>=0.1.0  # LangSmith SDK (lightweight, no LangChain)
```

**Note**: LangChain was removed due to Vercel size limits (250 MB). We use manual tracing instead.

