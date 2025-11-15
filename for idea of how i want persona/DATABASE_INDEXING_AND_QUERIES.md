# Database Indexing and Query Strategy

## Overview

The database uses **PostgreSQL with pgvector** for vector similarity search (RAG) and traditional B-tree indexes for relational queries. This document explains how data is indexed and queried.

---

## 1. Database Indexing Strategy

### 1.1 Traditional B-Tree Indexes

Used for filtering, joins, and exact lookups:

#### Users Table
```sql
CREATE INDEX idx_users_email ON users(email);                    -- Fast email lookups
CREATE INDEX idx_users_password_hash ON users(password_hash)     -- Auth queries
```

#### Sessions Table
```sql
CREATE INDEX idx_sessions_user_id ON sessions(user_id);          -- User's sessions
CREATE INDEX idx_sessions_project_id ON sessions(project_id);    -- Project filtering
CREATE INDEX idx_sessions_last_message_at ON sessions(last_message_at DESC);  -- Recent sessions
CREATE INDEX idx_sessions_is_active ON sessions(is_active);       -- Active session filtering
```

#### Chat Messages Table
```sql
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);  -- Messages by session
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);   -- Chronological order
CREATE INDEX idx_chat_messages_role ON chat_messages(role);               -- Filter by role
```

#### Assets Table
```sql
CREATE INDEX idx_assets_user_id ON assets(user_id);             -- User's assets
CREATE INDEX idx_assets_project_id ON assets(project_id);       -- Project assets
CREATE INDEX idx_assets_type ON assets(type);                   -- Filter by type
CREATE INDEX idx_assets_processing_status ON assets(processing_status);  -- Status filtering
```

### 1.2 Vector Indexes (pgvector)

Used for semantic similarity search in RAG:

#### Document Embeddings
```sql
CREATE INDEX idx_document_embeddings_vector ON document_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Index Type:** `ivfflat` (Inverted File with Flat Compression)
- **Algorithm:** Approximate Nearest Neighbor (ANN) search
- **Distance Function:** Cosine similarity (`vector_cosine_ops`)
- **Lists:** 100 (number of clusters for indexing)
- **Use Case:** Fast similarity search on document chunks

**Additional Indexes:**
```sql
CREATE INDEX idx_document_embeddings_asset ON document_embeddings(asset_id);      -- Find chunks by document
CREATE INDEX idx_document_embeddings_user ON document_embeddings(user_id);         -- User isolation
CREATE INDEX idx_document_embeddings_project ON document_embeddings(project_id);   -- Project filtering
```

#### Message Embeddings
```sql
CREATE INDEX idx_message_embeddings_vector ON message_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Additional Indexes:**
```sql
CREATE INDEX idx_message_embeddings_message ON message_embeddings(message_id);
CREATE INDEX idx_message_embeddings_user ON message_embeddings(user_id);
CREATE INDEX idx_message_embeddings_session ON message_embeddings(session_id);
```

#### Global Knowledge
```sql
CREATE INDEX idx_global_knowledge_vector ON global_knowledge 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Additional Indexes:**
```sql
CREATE INDEX idx_global_knowledge_category ON global_knowledge(category);          -- Filter by category
CREATE INDEX idx_global_knowledge_pattern_type ON global_knowledge(pattern_type); -- Filter by type
CREATE INDEX idx_global_knowledge_quality ON global_knowledge(quality_score DESC); -- Quality filtering
```

---

## 2. Query Patterns

### 2.1 Vector Similarity Queries (RAG)

All vector queries use **cosine similarity** via the `<=>` operator:

```sql
-- Similarity calculation: 1 - (embedding <=> query_embedding)
-- Result: 0.0 (dissimilar) to 1.0 (identical)
```

#### Document Chunk Retrieval
```sql
SELECT 
    embedding_id, asset_id, user_id, project_id,
    document_type, chunk_index, chunk_text, metadata,
    1 - (embedding <=> query_embedding) AS similarity
FROM document_embeddings
WHERE user_id = query_user_id
    AND (query_project_id IS NULL OR project_id = query_project_id)
    AND (1 - (embedding <=> query_embedding)) >= similarity_threshold
ORDER BY embedding <=> query_embedding  -- Closest first
LIMIT match_count;
```

**Query Flow:**
1. **Vector Index Scan:** Uses `ivfflat` index to find approximate nearest neighbors
2. **User Filter:** Filters by `user_id` (B-tree index)
3. **Project Filter:** Optional project filtering (B-tree index)
4. **Similarity Filter:** Removes results below threshold
5. **Sort:** Orders by distance (ascending = most similar)
6. **Limit:** Returns top N results

#### Message Retrieval
```sql
SELECT 
    embedding_id, message_id, user_id, project_id, session_id,
    content_snippet, role, metadata,
    1 - (embedding <=> query_embedding) AS similarity
FROM message_embeddings
WHERE user_id = query_user_id
    AND (query_project_id IS NULL OR project_id = query_project_id)
    AND (1 - (embedding <=> query_embedding)) >= similarity_threshold
ORDER BY embedding <=> query_embedding
LIMIT match_count;
```

#### Global Knowledge Retrieval
```sql
SELECT 
    knowledge_id, category, pattern_type, example_text,
    description, quality_score, tags, metadata,
    1 - (embedding <=> query_embedding) AS similarity
FROM global_knowledge
WHERE quality_score >= min_quality_score
    AND (1 - (embedding <=> query_embedding)) >= similarity_threshold
ORDER BY embedding <=> query_embedding
LIMIT match_count;
```

### 2.2 Traditional Relational Queries

#### Session Lookup
```sql
-- Uses: idx_sessions_user_id, idx_sessions_last_message_at
SELECT * FROM sessions
WHERE user_id = :user_id
ORDER BY last_message_at DESC
LIMIT 20;
```

#### Message History
```sql
-- Uses: idx_chat_messages_session_id, idx_chat_messages_created_at
SELECT * FROM chat_messages
WHERE session_id = :session_id
ORDER BY created_at ASC;
```

#### Asset Lookup
```sql
-- Uses: idx_assets_user_id, idx_assets_type
SELECT * FROM assets
WHERE user_id = :user_id
    AND type = 'document'
    AND processing_status = 'completed';
```

---

## 3. RAG Query Flow

### 3.1 Complete RAG Retrieval Process

```
User Query: "Who is my niche?"
    ↓
1. Query Expansion
   - Expand "my" → "brand niche target audience"
   - Add conversation context if available
    ↓
2. Generate Query Embedding
   - OpenAI text-embedding-3-small (1536 dimensions)
   - Embedding: [0.123, -0.456, ..., 0.789]
    ↓
3. Parallel Vector Searches
   ├─→ User Messages (message_embeddings)
   │   └─→ get_similar_user_messages()
   │       - Filter: user_id = X
   │       - Vector search: cosine similarity
   │       - Returns: Top 6 similar messages
   │
   ├─→ Document Chunks (document_embeddings)
   │   └─→ get_similar_document_chunks()
   │       - Filter: user_id = X, project_id = Y (optional)
   │       - Vector search: cosine similarity
   │       - Returns: Top 10 document chunks
   │
   └─→ Global Knowledge (global_knowledge)
       └─→ get_similar_global_knowledge()
           - Filter: quality_score >= 0.6
           - Vector search: cosine similarity
           - Returns: Top 3 patterns
    ↓
4. Context Building
   - Combine all results
   - Format for LLM prompt
   - Add metadata (similarity scores, sources)
    ↓
5. LLM Generation
   - Include RAG context in system prompt
   - Generate response using context
```

### 3.2 Query Implementation

**File:** `Simon-Backend/app/ai/rag_service.py`

```python
# Step 1: Generate query embedding
query_embedding = await embedding_service.generate_query_embedding(query_text)

# Step 2: Retrieve user messages (vector search)
user_context = await vector_storage.get_similar_user_messages(
    query_embedding=query_embedding,
    user_id=user_id,
    project_id=project_id,
    match_count=6,
    similarity_threshold=0.1  # Very low for testing
)

# Step 3: Retrieve document chunks (vector search)
document_context = await document_processor.get_document_context(
    query_embedding=query_embedding,
    user_id=user_id,
    project_id=project_id,
    match_count=10,
    similarity_threshold=0.1
)

# Step 4: Retrieve global knowledge (vector search)
global_context = await vector_storage.get_similar_global_knowledge(
    query_embedding=query_embedding,
    match_count=3,
    similarity_threshold=0.1,
    min_quality_score=0.6
)
```

**File:** `Simon-Backend/app/ai/vector_storage.py`

Uses Supabase RPC functions that execute the SQL queries above.

---

## 4. Index Performance Characteristics

### 4.1 Vector Index (ivfflat)

**Pros:**
- Fast approximate search (O(log n) vs O(n) for exact)
- Scales to millions of vectors
- Efficient for high-dimensional data (1536 dimensions)

**Cons:**
- Approximate results (may miss some similar vectors)
- Requires tuning `lists` parameter
- Index rebuild needed when data distribution changes significantly

**Tuning:**
- `lists = 100`: Good for ~10K-1M vectors
- For larger datasets, increase `lists` (rule of thumb: `lists = rows / 1000`)

### 4.2 B-Tree Indexes

**Pros:**
- Exact matches
- Fast lookups (O(log n))
- Efficient for filtering and joins

**Cons:**
- Not suitable for similarity search
- Requires maintenance on updates

---

## 5. Query Optimization

### 5.1 Current Optimizations

1. **User Isolation First:** Filter by `user_id` before vector search (reduces search space)
2. **Project Filtering:** Optional project filtering for multi-tenant scenarios
3. **Similarity Threshold:** Filters out low-quality matches early
4. **Limit Results:** Always uses `LIMIT` to cap result size
5. **Index Hints:** PostgreSQL optimizer uses indexes automatically

### 5.2 Query Performance

**Typical Query Times:**
- Vector search (10K vectors): ~10-50ms
- Vector search (100K vectors): ~50-200ms
- Vector search (1M vectors): ~200-1000ms
- B-tree lookups: <1ms

**Factors Affecting Performance:**
- Number of vectors in index
- `lists` parameter in ivfflat index
- Similarity threshold (lower = more results to filter)
- User/project filtering (reduces search space)

---

## 6. Index Maintenance

### 6.1 When to Rebuild Vector Indexes

Rebuild if:
- Data distribution changes significantly
- Performance degrades over time
- After bulk inserts/deletes

**Rebuild Command:**
```sql
REINDEX INDEX idx_document_embeddings_vector;
REINDEX INDEX idx_message_embeddings_vector;
REINDEX INDEX idx_global_knowledge_vector;
```

### 6.2 Index Statistics

PostgreSQL automatically updates statistics, but you can manually update:

```sql
ANALYZE document_embeddings;
ANALYZE message_embeddings;
ANALYZE global_knowledge;
```

---

## 7. Query Examples

### 7.1 Find Similar Documents

```python
# Python code
document_context = await document_processor.get_document_context(
    query_embedding=[0.123, -0.456, ...],  # 1536-dim vector
    user_id=UUID("..."),
    project_id=None,  # Search all projects
    match_count=10,
    similarity_threshold=0.1
)
```

**SQL Equivalent:**
```sql
SELECT * FROM get_similar_document_chunks(
    query_embedding := '[0.123, -0.456, ...]'::vector(1536),
    query_user_id := '...'::UUID,
    query_project_id := NULL,
    match_count := 10,
    similarity_threshold := 0.1
);
```

### 7.2 Find Similar Messages

```python
user_context = await vector_storage.get_similar_user_messages(
    query_embedding=query_embedding,
    user_id=user_id,
    project_id=project_id,
    match_count=6,
    similarity_threshold=0.1
)
```

**SQL Equivalent:**
```sql
SELECT * FROM get_similar_user_messages(
    query_embedding := '...'::vector(1536),
    query_user_id := '...'::UUID,
    query_project_id := NULL,
    match_count := 6,
    similarity_threshold := 0.1
);
```

---

## 8. Current Configuration

### 8.1 Vector Index Settings

- **Index Type:** `ivfflat`
- **Distance Function:** Cosine similarity (`vector_cosine_ops`)
- **Lists:** 100 (for all vector indexes)
- **Dimension:** 1536 (OpenAI text-embedding-3-small)

### 8.2 Similarity Thresholds

- **User Messages:** 0.1 (very low - ensures retrieval)
- **Document Chunks:** 0.1 (very low - ensures retrieval)
- **Global Knowledge:** 0.1 (very low) + quality_score >= 0.6

**Note:** Thresholds are intentionally low to ensure document retrieval works, even if similarity scores are lower than expected.

---

## 9. Performance Monitoring

### 9.1 Check Index Usage

```sql
-- See which indexes are being used
SELECT 
    schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('document_embeddings', 'message_embeddings', 'global_knowledge')
ORDER BY idx_scan DESC;
```

### 9.2 Check Query Performance

```sql
-- Enable query timing
\timing on

-- Test vector search
SELECT * FROM get_similar_document_chunks(
    query_embedding := (SELECT embedding FROM document_embeddings LIMIT 1),
    query_user_id := (SELECT user_id FROM document_embeddings LIMIT 1),
    match_count := 10,
    similarity_threshold := 0.1
);
```

---

## 10. Best Practices

1. **Always filter by user_id first** - Reduces search space dramatically
2. **Use appropriate similarity thresholds** - Balance between recall and precision
3. **Limit result counts** - Use `match_count` to cap results
4. **Monitor index usage** - Check `pg_stat_user_indexes` regularly
5. **Rebuild indexes periodically** - Especially after bulk operations
6. **Tune `lists` parameter** - Adjust based on data size

---

## Summary

- **Traditional Queries:** B-tree indexes for exact matches, filtering, joins
- **Vector Queries:** ivfflat indexes for semantic similarity search
- **Query Flow:** Generate embedding → Vector search → Filter by user/project → Return top N
- **Performance:** Optimized with user isolation, thresholds, and result limits
- **Maintenance:** Periodic index rebuilds and statistics updates

