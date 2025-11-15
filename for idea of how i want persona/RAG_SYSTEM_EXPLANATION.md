# RAG System Explanation - Current State

## Overview
The RAG (Retrieval Augmented Generation) system is **fully functional** and stores documents **permanently** in the Supabase database. Once a document is uploaded and processed, it becomes part of the knowledge base and does NOT need to be re-uploaded.

---

## How Document Ingestion Works

### 1. **Upload Process (Frontend → Backend)**

When you upload a document through the frontend:

1. **File Upload** (`/api/upload` endpoint):
   - File is uploaded to Supabase Storage (Supabase must be configured for full functionality)
   - Asset metadata is stored in `assets` table
   - Document text is extracted immediately for chat use
   - **Note**: Supabase is REQUIRED for RAG to work. Without it, documents cannot be stored or retrieved.

2. **RAG Processing** (Background Task):
   - Document is processed asynchronously via `process_document_for_rag()`
   - Text is extracted from PDF/DOCX/TXT files
   - Document is split into chunks (1000 chars per chunk, 200 char overlap)
   - Each chunk gets an embedding (1536-dimensional vector) via OpenAI
   - Embeddings are stored in `document_embeddings` table

### 2. **Storage Structure**

Documents are stored in **two tables**:

#### `assets` Table
- Stores file metadata (filename, URL, type, project_id)
- One record per uploaded file

#### `document_embeddings` Table
- Stores **chunks** of text with their embeddings
- Multiple rows per document (one per chunk)
- Each row contains:
  - `embedding_id`: Unique ID for the chunk
  - `asset_id`: Links to the original file
  - `user_id`: Owner of the document
  - `project_id`: Project context
  - `chunk_text`: The actual text content (up to 1000 chars)
  - `embedding`: Vector representation (1536 dimensions)
  - `metadata`: JSON with filename, chunk_size, content_type, etc.

**Key Point**: Documents are **permanently stored** in the database. Once ingested, they remain available for RAG retrieval until explicitly deleted.

---

## How RAG Retrieval Works

### 1. **Query Processing**

When a user asks a question:

1. **Query Expansion**:
   - Generic queries like "who am i" or "what's my niche" are expanded with brand keywords
   - Example: "who are my potential clients" → "who are my potential clients avatar sheet ICP ideal customer profile target audience..."
   - This helps match against the right documents

2. **Embedding Generation**:
   - User query is converted to an embedding vector (1536 dimensions)
   - Same embedding model as documents (OpenAI text-embedding-3-small)

3. **Similarity Search**:
   - Vector similarity search using cosine similarity
   - Searches across `document_embeddings` table
   - Returns top N most similar chunks (default: 10 chunks)

4. **Context Building**:
   - Retrieved chunks are formatted with metadata (filename, similarity score)
   - Organized by document type and use case
   - Combined with conversation history and global knowledge

5. **AI Response**:
   - Formatted context is sent to GPT-4o-mini
   - AI uses document context to answer questions
   - System prompt instructs AI on which documents to use for which questions

---

## Document Use Cases (Current Implementation)

The system recognizes different document types and uses them appropriately:

### **Avatar Sheet / ICP Document**
- **Use Case**: Questions about potential clients, target audience, niche
- **Example Queries**: "Who are my potential clients?", "What's my niche?", "Who is my target audience?"
- **How It Works**: Query expansion adds "avatar sheet ICP ideal customer profile" keywords

### **Script/Storytelling Documents**
- **Use Case**: Script creation, hooks, CTAs, storytelling structure
- **Example Queries**: "Create a script about...", "Write a hook for...", "What's my CTA format?"
- **How It Works**: Query expansion adds "script structure hook formulas CTA call to action" keywords

### **Content Strategy Documents**
- **Use Case**: Content ideas, weekly planning, content pillars
- **Example Queries**: "Give me content ideas", "What are my content pillars?", "Weekly content plan"
- **How It Works**: Query expansion adds "content strategy content pillars weekly planning" keywords

### **Carousel Documents**
- **Use Case**: Carousel creation rules and structure
- **Example Queries**: "Create a carousel about...", "What's my carousel structure?"
- **How It Works**: Query expansion adds "carousel rules carousel structure slides headline" keywords

### **North Star / Brand Vision**
- **Use Case**: Brand identity, tone, voice, overall approach
- **Example Queries**: "What's my tone?", "How should I write?", "What's my brand voice?"
- **How It Works**: Query expansion adds "tone voice writing style brand identity north star" keywords

---

## Current RAG Configuration

### Retrieval Settings
- **User Context**: Top 6 similar user messages
- **Global Knowledge**: Top 3 global patterns
- **Document Context**: Top 10 document chunks (configurable)
- **Similarity Threshold**: 0.1 (very low - retrieves most relevant chunks)

### Chunking Settings
- **Chunk Size**: 1000 characters per chunk
- **Chunk Overlap**: 200 characters
- **Max Chunks**: 50 chunks per document (prevents excessive embeddings)

### Embedding Model
- **Model**: OpenAI `text-embedding-3-small`
- **Dimensions**: 1536
- **Cost**: ~$0.02 per 1M tokens

---

## Answering Your Questions

### ✅ **Q: When we ingest a document through the frontend, does it get stored forever in the knowledge base?**
**A: YES.** Documents are permanently stored in the `document_embeddings` table. Each chunk of text is stored with its embedding vector. Once ingested, the document remains in the knowledge base until explicitly deleted.

### ✅ **Q: We don't have to upload that doc again ever then right?**
**A: CORRECT.** Once a document is uploaded and processed, it's in the knowledge base permanently. You only need to upload it once. The system will retrieve relevant chunks from it during every chat query.

### ✅ **Q: Need to understand the extent of RAG and retrieval process**
**A: Here's the full flow:**

1. **Ingestion** (One-time per document):
   - Upload → Extract text → Split into chunks → Generate embeddings → Store in database
   - Time: ~5-30 seconds depending on document size
   - Result: Document is now searchable

2. **Retrieval** (Every chat query):
   - User question → Expand query → Generate embedding → Search database → Retrieve top chunks → Format context → Send to AI
   - Time: ~1-3 seconds
   - Result: AI gets relevant document context

3. **Response** (Every chat query):
   - AI receives context + system prompt → Generates response using document information
   - Time: ~2-5 seconds
   - Result: Brand-aligned response

---

## What You Need to Know for New Documents

### **Document 1: Simon's Description About Himself**
- **Purpose**: Personal information, background, expertise
- **Use Case**: Questions like "Tell me about yourself", "What's your background?", "Who are you?"
- **How to Ingest**: Upload via frontend, system will automatically process and store
- **Query Matching**: Will match queries about personal info, background, expertise

### **Document 2: Document Explanation (How Chatbot Uses Documents)**
- **Purpose**: Instructions for the AI on how to use different documents
- **Use Case**: This is **meta-instruction** - tells the AI which documents to use for which questions
- **How to Ingest**: Upload via frontend, system will process and store
- **Query Matching**: Will match queries about document usage, but more importantly, it will be included in context to guide the AI

**Important**: The "Document Explanation" document should contain clear instructions like:
- "When asked about niche/clients → Use Avatar Sheet document"
- "When asked to create scripts → Use Script/Storytelling documents"
- "When asked about tone → Use North Star document"

The AI's system prompt already has these instructions, but having them in a document ensures they're always in context.

---

## Current Limitations & Considerations

### 1. **No Document Deletion UI**
- Documents are stored permanently
- To delete, you'd need to manually delete from `document_embeddings` table
- Future: Add document management UI

### 2. **No Document Update Mechanism**
- If you update a document, you need to:
  1. Delete old embeddings (by asset_id)
  2. Re-upload the new document
- Future: Add document versioning

### 3. **Chunking Limitations**
- Documents are split into 1000-char chunks
- Very long documents may have many chunks
- Context window limits how many chunks can be used (currently ~10 chunks)

### 4. **Similarity Threshold**
- Currently set to 0.1 (very low)
- This means almost all chunks are retrieved
- May need tuning based on document quality

---

## Testing RAG Retrieval

### Check if Documents Are Stored
```bash
# Use the debug endpoint
GET /api/ingest/debug/embeddings?limit=10
```

### Check Ingestion Status
```bash
GET /api/ingest/status
```

### Test Queries
1. "Who are my potential clients?" → Should retrieve Avatar Sheet chunks
2. "Create a script about consistency" → Should retrieve Script/Storytelling chunks
3. "What's my tone?" → Should retrieve North Star/Brand Vision chunks

---

## Next Steps for Your Two Documents

1. **Upload Simon's Description**:
   - Upload via frontend
   - Wait for processing (~5-30 seconds)
   - Test with: "Tell me about yourself" or "Who is Simon?"

2. **Upload Document Explanation**:
   - Upload via frontend
   - Wait for processing
   - This document will be included in context to guide the AI
   - Test with queries that should use specific documents

3. **Verify Retrieval**:
   - Check logs for "✅ [RAG] Retrieved X document chunks"
   - Verify correct documents are being retrieved for each query type

---

## Summary

✅ **Documents are stored permanently** - Once uploaded, they're in the knowledge base forever  
✅ **No need to re-upload** - Documents are retrieved automatically during chat  
✅ **RAG is fully functional** - Query expansion, similarity search, and context building all work  
✅ **Document use cases are recognized** - System knows which documents to use for which questions  
✅ **Ready for new documents** - Just upload and they'll be processed automatically  

The system is production-ready for document ingestion and retrieval. The main thing to ensure is that your documents have clear, descriptive filenames and content that matches the query patterns (e.g., "Avatar Sheet" for client questions, "Script Guide" for script questions).

