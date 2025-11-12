-- Alternative Migration: Add session_id filter to RAG retrieval
-- Use this if the main migration fails due to function overloading

-- Simple approach: Drop all functions with this name (CASCADE handles dependencies)
DROP FUNCTION IF EXISTS get_similar_user_messages CASCADE;

-- Create the updated function with session_id parameter
CREATE FUNCTION get_similar_user_messages(
    query_embedding vector(1536),
    query_user_id UUID,
    query_project_id UUID DEFAULT NULL,
    query_session_id UUID DEFAULT NULL,  -- NEW: Filter by session_id
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
        1 - (me.embedding <=> query_embedding) AS similarity
    FROM message_embeddings me
    WHERE me.user_id = query_user_id
        AND (query_project_id IS NULL OR me.project_id = query_project_id)
        AND (query_session_id IS NULL OR me.session_id = query_session_id)  -- NEW: Session filter
        AND (1 - (me.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY me.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION get_similar_user_messages IS 'RAG: Find similar chat messages using vector similarity. Now filters by session_id to ensure session isolation.';

