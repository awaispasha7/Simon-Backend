# RAG System Improvements: Indexing, Querying, and Response Optimization

## Overview

This document outlines concrete improvements to enhance RAG (Retrieval-Augmented Generation) performance, accuracy, and response quality.

---

## 1. Indexing Improvements

### 1.1 Enhanced Chunking Strategy

**Current State:**
- Fixed-size chunks (1000 chars) with 200 char overlap
- Simple sentence/word boundary detection
- No semantic awareness

**Improvements:**

#### A. Semantic Chunking
Split documents based on semantic meaning rather than fixed size:

```python
# In document_processor.py
def _semantic_chunk_text(self, text: str) -> List[Dict[str, str]]:
    """
    Split text into semantically meaningful chunks
    Uses sentence embeddings to find natural break points
    """
    # Split into sentences first
    sentences = self._split_into_sentences(text)
    
    # Generate embeddings for each sentence
    sentence_embeddings = await self._get_embeddings(sentences)
    
    # Group sentences with similar embeddings
    chunks = []
    current_chunk = []
    current_embedding = None
    
    for sentence, embedding in zip(sentences, sentence_embeddings):
        if current_embedding is None:
            current_chunk.append(sentence)
            current_embedding = embedding
        else:
            # Calculate similarity
            similarity = cosine_similarity([current_embedding], [embedding])[0][0]
            
            if similarity > 0.85 and len(' '.join(current_chunk)) < self.max_chunk_size:
                # Similar topic, add to current chunk
                current_chunk.append(sentence)
                # Update centroid embedding
                current_embedding = np.mean([current_embedding, embedding], axis=0)
            else:
                # New topic, save current chunk
                if current_chunk:
                    chunks.append({
                        'text': ' '.join(current_chunk),
                        'type': 'semantic',
                        'sentence_count': len(current_chunk)
                    })
                current_chunk = [sentence]
                current_embedding = embedding
    
    return chunks
```

**Benefits:**
- Preserves semantic coherence
- Better context preservation
- Improved retrieval accuracy

#### B. Hierarchical Chunking
Create multiple chunk sizes for different retrieval needs:

```python
def _hierarchical_chunk(self, text: str) -> Dict[str, List[str]]:
    """
    Create chunks at multiple granularities:
    - Small (200 chars): For precise matching
    - Medium (1000 chars): Current default
    - Large (3000 chars): For broad context
    """
    return {
        'small': self._split_text_into_chunks(text, chunk_size=200, overlap=50),
        'medium': self._split_text_into_chunks(text, chunk_size=1000, overlap=200),
        'large': self._split_text_into_chunks(text, chunk_size=3000, overlap=500)
    }
```

**Benefits:**
- Flexible retrieval (use small for precision, large for context)
- Better coverage of different query types

#### C. Document Structure Awareness
Preserve document structure (headers, sections, lists):

```python
def _structure_aware_chunk(self, text: str, metadata: Dict) -> List[Dict[str, Any]]:
    """
    Chunk while preserving document structure
    """
    chunks = []
    
    # Detect sections (headers, paragraphs, lists)
    sections = self._detect_sections(text)
    
    for section in sections:
        section_text = section['content']
        section_type = section['type']  # 'header', 'paragraph', 'list'
        
        # Chunk within section boundaries
        section_chunks = self._split_text_into_chunks(section_text)
        
        for chunk in section_chunks:
            chunks.append({
                'text': chunk,
                'section_type': section_type,
                'section_title': section.get('title', ''),
                'chunk_index': len(chunks),
                'metadata': {
                    **metadata,
                    'section_context': section.get('context', '')
                }
            })
    
    return chunks
```

### 1.2 Metadata Enrichment

**Current State:**
- Basic metadata (filename, document_type, chunk_index)
- Limited context information

**Improvements:**

```python
# Enhanced metadata for each chunk
chunk_metadata = {
    'filename': filename,
    'document_type': doc_type,
    'chunk_index': chunk_index,
    'chunk_size': len(chunk_text),
    'section_title': section_title,  # NEW
    'section_type': section_type,     # NEW
    'document_section': doc_section,  # NEW (e.g., "Introduction", "Rules", "Examples")
    'importance_score': importance,   # NEW (based on position, headers, etc.)
    'keywords': extracted_keywords,   # NEW (top keywords in chunk)
    'entities': extracted_entities,   # NEW (named entities)
    'topic': detected_topic,          # NEW (topic classification)
    'created_at': timestamp,
    'updated_at': timestamp
}
```

**Benefits:**
- Better filtering and ranking
- Context-aware retrieval
- Improved relevance

### 1.3 Index Optimization

**Current State:**
- `ivfflat` index with 100 lists
- Fixed configuration

**Improvements:**

#### A. Dynamic Index Tuning
```sql
-- Adjust lists based on data size
-- Rule of thumb: lists = sqrt(rows) for optimal performance

-- For 10K vectors: lists = 100 (current)
-- For 100K vectors: lists = 316
-- For 1M vectors: lists = 1000

-- Rebuild index with optimal parameters
CREATE INDEX idx_document_embeddings_vector_v2 ON document_embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 316);  -- Adjust based on row count
```

#### B. HNSW Index (Alternative)
For better accuracy at scale:

```sql
-- HNSW provides better recall than ivfflat
CREATE INDEX idx_document_embeddings_hnsw ON document_embeddings 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**Trade-offs:**
- **ivfflat**: Faster build, lower memory, approximate
- **HNSW**: Better accuracy, higher memory, slower build

---

## 2. Query Improvements

### 2.1 Query Expansion and Rewriting

**Current State:**
- Basic query expansion for brand terms
- No query rewriting

**Improvements:**

#### A. Multi-Query Generation
Generate multiple query variations:

```python
async def _generate_query_variations(self, user_query: str) -> List[str]:
    """
    Generate multiple query variations for better retrieval
    """
    variations = [user_query]  # Original query
    
    # 1. Expand with synonyms
    expanded = self._expand_with_synonyms(user_query)
    variations.append(expanded)
    
    # 2. Generate question variations
    if '?' in user_query:
        # Convert question to statement
        variations.append(self._question_to_statement(user_query))
    else:
        # Convert statement to question
        variations.append(self._statement_to_question(user_query))
    
    # 3. Extract key terms and create focused queries
    key_terms = self._extract_key_terms(user_query)
    if key_terms:
        variations.append(' '.join(key_terms))
    
    # 4. Generate embedding for each variation
    query_embeddings = []
    for variation in variations:
        embedding = await self._get_embedding_service().generate_query_embedding(variation)
        query_embeddings.append(embedding)
    
    # 5. Retrieve with each variation, then merge and deduplicate
    all_results = []
    for embedding in query_embeddings:
        results = await self._retrieve_with_embedding(embedding)
        all_results.extend(results)
    
    # Deduplicate and re-rank
    return self._deduplicate_and_rerank(all_results)
```

#### B. Query Classification
Classify query type to optimize retrieval:

```python
def _classify_query(self, query: str) -> Dict[str, Any]:
    """
    Classify query to determine retrieval strategy
    """
    query_lower = query.lower()
    
    # Question types
    if any(word in query_lower for word in ['who', 'what', 'where', 'when', 'why', 'how']):
        query_type = 'factual'
        strategy = 'precise_chunks'  # Use smaller chunks
    elif any(word in query_lower for word in ['create', 'make', 'generate', 'write']):
        query_type = 'generative'
        strategy = 'broad_context'  # Use larger chunks
    elif any(word in query_lower for word in ['my', 'me', 'i']):
        query_type = 'personal'
        strategy = 'user_documents'  # Prioritize user docs
    else:
        query_type = 'general'
        strategy = 'balanced'
    
    return {
        'type': query_type,
        'strategy': strategy,
        'needs_expansion': query_type in ['factual', 'personal']
    }
```

### 2.2 Hybrid Search (Vector + Keyword)

**Current State:**
- Vector search only
- No keyword matching

**Improvements:**

```python
async def _hybrid_search(
    self,
    query_embedding: List[float],
    query_text: str,
    user_id: UUID,
    project_id: Optional[UUID] = None
) -> List[Dict[str, Any]]:
    """
    Combine vector search with keyword search (BM25)
    """
    # 1. Vector search (semantic)
    vector_results = await self._vector_search(
        query_embedding=query_embedding,
        user_id=user_id,
        project_id=project_id,
        match_count=20  # Get more candidates
    )
    
    # 2. Keyword search (exact matching)
    keyword_results = await self._keyword_search(
        query_text=query_text,
        user_id=user_id,
        project_id=project_id,
        match_count=20
    )
    
    # 3. Combine and re-rank
    combined_results = self._combine_results(vector_results, keyword_results)
    
    # 4. Re-rank with cross-encoder or reciprocal rank fusion
    reranked = self._rerank_results(combined_results, query_text)
    
    return reranked[:10]  # Return top 10

def _rerank_results(
    self,
    results: List[Dict[str, Any]],
    query: str
) -> List[Dict[str, Any]]:
    """
    Re-rank results using reciprocal rank fusion (RRF)
    """
    # RRF formula: score = sum(1 / (k + rank))
    # k = 60 (typical value)
    
    ranked_results = {}
    
    for result in results:
        result_id = result.get('embedding_id') or result.get('chunk_id')
        vector_rank = result.get('vector_rank', 999)
        keyword_rank = result.get('keyword_rank', 999)
        
        # Calculate RRF score
        rrf_score = (1 / (60 + vector_rank)) + (1 / (60 + keyword_rank))
        
        result['rrf_score'] = rrf_score
        ranked_results[result_id] = result
    
    # Sort by RRF score
    sorted_results = sorted(
        ranked_results.values(),
        key=lambda x: x['rrf_score'],
        reverse=True
    )
    
    return sorted_results
```

**Benefits:**
- Better recall (finds both semantically similar and exact matches)
- Improved precision
- Handles queries with specific terms better

### 2.3 Re-ranking with Cross-Encoders

**Improvement:**

```python
# Optional: Use a cross-encoder model for re-ranking
# This provides better accuracy but requires additional model

async def _rerank_with_cross_encoder(
    self,
    query: str,
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Re-rank candidates using a cross-encoder model
    (More accurate but slower than RRF)
    """
    # This would require a cross-encoder model (e.g., sentence-transformers)
    # For now, use RRF as it's faster and doesn't require additional models
    
    # Example implementation (if cross-encoder available):
    # from sentence_transformers import CrossEncoder
    # model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    # 
    # pairs = [(query, candidate['chunk_text']) for candidate in candidates]
    # scores = model.predict(pairs)
    # 
    # for candidate, score in zip(candidates, scores):
    #     candidate['rerank_score'] = float(score)
    # 
    # return sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
    
    pass
```

---

## 3. Response Improvements

### 3.1 Context Compression

**Current State:**
- All retrieved chunks included in full
- Can exceed token limits
- May include irrelevant information

**Improvements:**

```python
def _compress_context(
    self,
    retrieved_chunks: List[Dict[str, Any]],
    query: str,
    max_tokens: int = 4000
) -> str:
    """
    Compress context to fit within token limits while preserving relevance
    """
    # 1. Sort by relevance score
    sorted_chunks = sorted(
        retrieved_chunks,
        key=lambda x: x.get('similarity', 0),
        reverse=True
    )
    
    # 2. Select chunks until token limit
    compressed_context = []
    current_tokens = 0
    
    for chunk in sorted_chunks:
        chunk_text = chunk.get('chunk_text', '')
        chunk_tokens = len(chunk_text.split()) * 1.3  # Approximate token count
        
        if current_tokens + chunk_tokens <= max_tokens:
            compressed_context.append(chunk)
            current_tokens += chunk_tokens
        else:
            # Try to include partial chunk if it's highly relevant
            if chunk.get('similarity', 0) > 0.8:
                remaining_tokens = max_tokens - current_tokens
                # Truncate chunk to fit
                words = chunk_text.split()
                max_words = int(remaining_tokens / 1.3)
                truncated = ' '.join(words[:max_words])
                compressed_context.append({
                    **chunk,
                    'chunk_text': truncated + '...',
                    'truncated': True
                })
            break
    
    # 3. Format compressed context
    return self._format_rag_context(compressed_context)
```

### 3.2 Relevance Filtering

**Improvement:**

```python
def _filter_by_relevance(
    self,
    results: List[Dict[str, Any]],
    min_similarity: float = 0.3,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Filter results by relevance score and diversity
    """
    # 1. Filter by similarity threshold
    filtered = [
        r for r in results
        if r.get('similarity', 0) >= min_similarity
    ]
    
    # 2. Diversity filtering (avoid duplicate content)
    diverse_results = []
    seen_content = set()
    
    for result in filtered:
        content_hash = hash(result.get('chunk_text', '')[:100])
        if content_hash not in seen_content:
            diverse_results.append(result)
            seen_content.add(content_hash)
            
            if len(diverse_results) >= max_results:
                break
    
    return diverse_results
```

### 3.3 Citation Tracking

**Improvement:**

```python
def _format_context_with_citations(
    self,
    chunks: List[Dict[str, Any]]
) -> str:
    """
    Format context with proper citations for traceability
    """
    formatted = []
    
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.get('metadata', {}).get('filename', 'Unknown')
        chunk_index = chunk.get('chunk_index', 0)
        similarity = chunk.get('similarity', 0)
        
        formatted.append(f"[{i}] Source: {filename} (Chunk {chunk_index}, Relevance: {similarity:.2f})")
        formatted.append(chunk.get('chunk_text', ''))
        formatted.append("")
    
    return "\n".join(formatted)
```

---

## 4. Implementation Priority

### Phase 1: Quick Wins (1-2 days)
1. ✅ **Metadata Enrichment** - Add section titles, keywords, importance scores
2. ✅ **Relevance Filtering** - Filter low-relevance results
3. ✅ **Context Compression** - Ensure context fits token limits
4. ✅ **Query Classification** - Optimize retrieval strategy based on query type

### Phase 2: Medium Effort (3-5 days)
1. ✅ **Hybrid Search** - Combine vector + keyword search
2. ✅ **Multi-Query Generation** - Generate query variations
3. ✅ **Structure-Aware Chunking** - Preserve document structure
4. ✅ **Index Tuning** - Optimize ivfflat parameters

### Phase 3: Advanced (1-2 weeks)
1. ✅ **Semantic Chunking** - Chunk based on semantic meaning
2. ✅ **Hierarchical Chunking** - Multiple chunk sizes
3. ✅ **Cross-Encoder Re-ranking** - Advanced re-ranking (if model available)
4. ✅ **HNSW Index** - Switch to HNSW for better accuracy

---

## 5. Performance Metrics to Track

1. **Retrieval Metrics:**
   - Recall@K (how many relevant docs found in top K)
   - Precision@K (how many of top K are relevant)
   - Mean Reciprocal Rank (MRR)

2. **Response Quality:**
   - Answer accuracy (manual evaluation)
   - Citation accuracy
   - Context relevance

3. **Performance:**
   - Query latency
   - Index size
   - Memory usage

---

## 6. Code Examples

### Example: Enhanced Document Processing

```python
# In document_processor.py

async def process_document_enhanced(
    self,
    asset_id: UUID,
    user_id: UUID,
    project_id: UUID,
    file_content: bytes,
    filename: str,
    content_type: str
) -> Dict[str, Any]:
    """
    Enhanced document processing with better chunking and metadata
    """
    # Extract text
    text_content = await self._extract_text(file_content, filename, content_type)
    
    # Detect document structure
    structure = self._detect_document_structure(text_content)
    
    # Create hierarchical chunks
    chunks_data = []
    
    for section in structure['sections']:
        # Chunk within section
        section_chunks = self._split_text_into_chunks(
            section['content'],
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap
        )
        
        for idx, chunk_text in enumerate(section_chunks):
            # Extract metadata
            metadata = {
                'filename': filename,
                'document_type': self._get_document_type(filename),
                'section_title': section.get('title', ''),
                'section_type': section.get('type', 'paragraph'),
                'chunk_index': idx,
                'importance_score': self._calculate_importance(section, idx),
                'keywords': self._extract_keywords(chunk_text),
                'topic': self._classify_topic(chunk_text)
            }
            
            # Generate embedding
            embedding = await self._get_embedding_service().generate_embedding(chunk_text)
            
            # Store
            await self.vector_storage.store_document_embedding(
                asset_id=asset_id,
                user_id=user_id,
                project_id=project_id,
                document_type=metadata['document_type'],
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=embedding,
                metadata=metadata
            )
            
            chunks_data.append({
                'chunk_text': chunk_text,
                'metadata': metadata
            })
    
    return {
        'success': True,
        'chunks_processed': len(chunks_data),
        'sections_detected': len(structure['sections'])
    }
```

### Example: Enhanced RAG Query

```python
# In rag_service.py

async def get_rag_context_enhanced(
    self,
    user_message: str,
    user_id: UUID,
    project_id: Optional[UUID] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Enhanced RAG context retrieval with hybrid search and re-ranking
    """
    # 1. Classify query
    query_info = self._classify_query(user_message)
    
    # 2. Expand query
    expanded_query = self._expand_brand_query(user_message)
    
    # 3. Generate query variations
    query_variations = await self._generate_query_variations(expanded_query)
    
    # 4. Generate embeddings for each variation
    query_embeddings = []
    for variation in query_variations:
        embedding = await self._get_embedding_service().generate_query_embedding(variation)
        query_embeddings.append(embedding)
    
    # 5. Hybrid search (vector + keyword)
    all_results = []
    
    for query_embedding in query_embeddings:
        # Vector search
        vector_results = await self.vector_storage.get_similar_user_messages(
            query_embedding=query_embedding,
            user_id=user_id,
            project_id=project_id,
            match_count=20,  # Get more candidates
            similarity_threshold=0.1
        )
        
        # Keyword search (if query has specific terms)
        if query_info['needs_expansion']:
            keyword_results = await self._keyword_search(
                query_text=expanded_query,
                user_id=user_id,
                project_id=project_id
            )
            all_results.extend(keyword_results)
        
        all_results.extend(vector_results)
    
    # 6. Re-rank with RRF
    reranked_results = self._rerank_results(all_results, expanded_query)
    
    # 7. Filter by relevance and diversity
    filtered_results = self._filter_by_relevance(
        reranked_results,
        min_similarity=0.3,
        max_results=10
    )
    
    # 8. Format context
    combined_context = self._format_rag_context(filtered_results)
    
    return {
        'combined_context_text': combined_context,
        'metadata': {
            'query_type': query_info['type'],
            'results_count': len(filtered_results),
            'avg_similarity': sum(r.get('similarity', 0) for r in filtered_results) / len(filtered_results) if filtered_results else 0
        }
    }
```

---

## 7. Testing and Validation

### Test Cases:

1. **Precision Test:**
   - Query: "Who is my niche?"
   - Expected: Retrieve chunks from Avatar Sheet/ICP document
   - Measure: Precision@5, Precision@10

2. **Recall Test:**
   - Query: "What are the script rules?"
   - Expected: Retrieve all relevant chunks from Script documents
   - Measure: Recall@10, Recall@20

3. **Diversity Test:**
   - Query: "Tell me about my brand"
   - Expected: Retrieve chunks from multiple documents (not duplicates)
   - Measure: Document diversity, chunk diversity

---

## Summary

**Key Improvements:**
1. **Better Chunking:** Semantic, hierarchical, structure-aware
2. **Enhanced Metadata:** More context for better filtering
3. **Hybrid Search:** Vector + keyword for better recall
4. **Query Optimization:** Multi-query, classification, expansion
5. **Re-ranking:** RRF or cross-encoder for better precision
6. **Context Management:** Compression, filtering, citations

**Expected Impact:**
- **Retrieval Accuracy:** +20-30% improvement
- **Response Quality:** Better context, more relevant answers
- **Performance:** Optimized for scale

Start with Phase 1 improvements for quick wins, then gradually implement Phase 2 and 3 based on performance metrics.

