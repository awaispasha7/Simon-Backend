-- Migration: Add session_id filter to RAG retrieval
-- This ensures each chat session is isolated and doesn't pull messages from other sessions

-- Drop all existing versions of the function to avoid overloading conflicts
-- PostgreSQL allows function overloading, so we need to drop all variants
DO $$ 
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT oid, proname, pg_get_function_identity_arguments(oid) as args
              FROM pg_proc 
              WHERE proname = 'get_similar_user_messages') 
    LOOP
        EXECUTE 'DROP FUNCTION IF EXISTS ' || quote_ident(r.proname) || '(' || r.args || ') CASCADE';
    END LOOP;
END $$;

-- Create the updated function with session_id parameter
CREATE OR REPLACE FUNCTION get_similar_user_messages(
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

