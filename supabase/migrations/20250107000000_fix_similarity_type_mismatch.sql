-- ============================================================================
-- Fix: Type mismatch in RPC functions - similarity returns double precision
-- but function signature expects NUMERIC
-- ============================================================================

-- Fix get_similar_user_messages: Cast similarity to NUMERIC
CREATE OR REPLACE FUNCTION get_similar_user_messages(
    query_embedding vector(1536),
    query_user_id UUID,
    query_project_id UUID DEFAULT NULL,
    match_count INTEGER DEFAULT 5,
    similarity_threshold NUMERIC DEFAULT 0.7
)
RETURNS TABLE (
    embedding_id UUID,
    message_id UUID,
    user_id UUID,
    project_id UUID,
    session_id UUID,
    content_snippet TEXT,
    role TEXT,
    metadata JSONB,
    similarity NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        me.embedding_id,
        me.message_id,
        me.user_id,
        me.project_id,
        me.session_id,
        me.content_snippet,
        me.role,
        me.metadata,
        (1 - (me.embedding <=> query_embedding))::NUMERIC AS similarity
    FROM message_embeddings me
    WHERE me.user_id = query_user_id
        AND (query_project_id IS NULL OR me.project_id = query_project_id)
        AND (1 - (me.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY me.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Fix get_similar_global_knowledge: Cast similarity to NUMERIC
CREATE OR REPLACE FUNCTION get_similar_global_knowledge(
    query_embedding vector(1536),
    match_count INTEGER DEFAULT 5,
    similarity_threshold NUMERIC DEFAULT 0.7,
    min_quality_score NUMERIC DEFAULT 0.6
)
RETURNS TABLE (
    knowledge_id UUID,
    category TEXT,
    pattern_type TEXT,
    example_text TEXT,
    description TEXT,
    quality_score NUMERIC,
    tags TEXT[],
    metadata JSONB,
    similarity NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gk.knowledge_id,
        gk.category,
        gk.pattern_type,
        gk.example_text,
        gk.description,
        gk.quality_score,
        gk.tags,
        gk.metadata,
        (1 - (gk.embedding <=> query_embedding))::NUMERIC AS similarity
    FROM global_knowledge gk
    WHERE gk.quality_score >= min_quality_score
        AND (1 - (gk.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY gk.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Also fix get_similar_document_chunks for consistency (even though it might work)
CREATE OR REPLACE FUNCTION get_similar_document_chunks(
    query_embedding vector(1536),
    query_user_id UUID,
    query_project_id UUID DEFAULT NULL,
    match_count INTEGER DEFAULT 5,
    similarity_threshold NUMERIC DEFAULT 0.7
)
RETURNS TABLE (
    embedding_id UUID,
    asset_id UUID,
    user_id UUID,
    project_id UUID,
    document_type TEXT,
    chunk_index INTEGER,
    chunk_text TEXT,
    metadata JSONB,
    similarity NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        de.embedding_id,
        de.asset_id,
        de.user_id,
        de.project_id,
        de.document_type,
        de.chunk_index,
        de.chunk_text,
        de.metadata,
        (1 - (de.embedding <=> query_embedding))::NUMERIC AS similarity
    FROM document_embeddings de
    WHERE de.user_id = query_user_id
        AND (query_project_id IS NULL OR de.project_id = query_project_id)
        AND (1 - (de.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

