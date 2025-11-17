-- Migration: Update RPC functions to remove project_id references
-- This script updates the database functions to work without projects

-- Drop existing functions first (required when return type changes)
DROP FUNCTION IF EXISTS get_similar_document_chunks(vector, uuid, uuid, integer, numeric);
DROP FUNCTION IF EXISTS get_similar_document_chunks(vector, uuid, integer, numeric);
DROP FUNCTION IF EXISTS get_similar_user_messages(vector, uuid, uuid, uuid, integer, numeric);
DROP FUNCTION IF EXISTS get_similar_user_messages(vector, uuid, uuid, integer, numeric);
DROP FUNCTION IF EXISTS get_user_sessions(uuid, integer);

-- 1. Update get_similar_document_chunks to remove project_id
CREATE FUNCTION get_similar_document_chunks(
    query_embedding vector,
    query_user_id uuid,
    match_count integer DEFAULT 5,
    similarity_threshold numeric DEFAULT 0.7
)
RETURNS TABLE (
    embedding_id uuid,
    asset_id uuid,
    user_id uuid,
    document_type text,
    chunk_index integer,
    chunk_text text,
    metadata jsonb,
    similarity numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        de.embedding_id,
        de.asset_id,
        de.user_id,
        de.document_type,
        de.chunk_index,
        de.chunk_text,
        de.metadata,
        (1 - (de.embedding <=> query_embedding))::NUMERIC AS similarity
    FROM document_embeddings de
    WHERE de.user_id = query_user_id
        AND (1 - (de.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 2. Update get_similar_user_messages to remove project_id
CREATE FUNCTION get_similar_user_messages(
    query_embedding vector,
    query_user_id uuid,
    query_session_id uuid DEFAULT NULL,
    match_count integer DEFAULT 10,
    similarity_threshold numeric DEFAULT 0.7
)
RETURNS TABLE (
    embedding_id uuid,
    message_id uuid,
    user_id uuid,
    session_id uuid,
    content_snippet text,
    role text,
    metadata jsonb,
    similarity numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        me.embedding_id,
        me.message_id,
        me.user_id,
        me.session_id,
        me.content_snippet,
        me.role,
        me.metadata,
        (1 - (me.embedding <=> query_embedding))::NUMERIC AS similarity
    FROM message_embeddings me
    WHERE me.user_id = query_user_id
        AND (query_session_id IS NULL OR me.session_id = query_session_id)
        AND (1 - (me.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY me.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 3. Update get_user_sessions to remove project_id
CREATE FUNCTION get_user_sessions(
    p_user_id uuid,
    p_limit integer DEFAULT 10
)
RETURNS TABLE (
    session_id uuid,
    title text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    last_message_at timestamp with time zone,
    message_count bigint,
    last_message_preview text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.session_id,
        s.title,
        s.created_at,
        s.updated_at,
        s.last_message_at,
        COUNT(cm.message_id) as message_count,
        (
            SELECT content 
            FROM chat_messages 
            WHERE session_id = s.session_id 
            ORDER BY created_at DESC 
            LIMIT 1
        ) as last_message_preview
    FROM sessions s
    LEFT JOIN chat_messages cm ON s.session_id = cm.session_id
    WHERE s.user_id = p_user_id AND s.is_active = true
    GROUP BY s.session_id, s.title, s.created_at, s.updated_at, s.last_message_at
    ORDER BY s.last_message_at DESC
    LIMIT p_limit;
END;
$$;

-- Note: get_session_messages, get_similar_global_knowledge, and verify_user_credentials
-- don't need updates as they don't reference project_id

