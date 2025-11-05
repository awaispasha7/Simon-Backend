-- ============================================================================
-- Complete Supabase Setup - No RLS, No Dossier
-- Migration: 20250121000000_complete_setup_no_rls_no_dossier.sql
-- ============================================================================
-- This migration sets up all required tables for the Coach Strategist AI
-- WITHOUT Row Level Security (RLS) and WITHOUT dossier functionality
-- ============================================================================

-- ============================================================================
-- STEP 1: Enable pgvector Extension (Required for RAG)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- STEP 2: Create Core Tables
-- ============================================================================

-- 2.1: Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    password_hash TEXT, -- For password authentication
    created_at TIMESTAMPTZ DEFAULT current_timestamp,
    updated_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Index for email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_password_hash ON users(password_hash) WHERE password_hash IS NOT NULL;

-- 2.2: Sessions Table (NO dossier reference)
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    project_id UUID, -- Optional UUID for grouping sessions (NO foreign key to dossier)
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT current_timestamp,
    updated_at TIMESTAMPTZ DEFAULT current_timestamp,
    last_message_at TIMESTAMPTZ DEFAULT current_timestamp,
    is_active BOOLEAN DEFAULT true
);

-- Indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_last_message_at ON sessions(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON sessions(is_active);

-- 2.3: Chat Messages Table
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT current_timestamp,
    updated_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Indexes for chat_messages
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);

-- 2.4: User Projects Table (for project ownership, NO dossier reference)
CREATE TABLE IF NOT EXISTS user_projects (
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    project_id UUID NOT NULL, -- Just a UUID identifier, no foreign key
    project_name TEXT, -- Optional name for the project
    created_at TIMESTAMPTZ DEFAULT current_timestamp,
    PRIMARY KEY (user_id, project_id)
);

-- Indexes for user_projects
CREATE INDEX IF NOT EXISTS idx_user_projects_user_id ON user_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_project_id ON user_projects(project_id);

-- 2.5: Assets Table (for file storage)
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID, -- Optional project reference (NO foreign key)
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- 'image', 'document', 'video', etc.
    uri TEXT NOT NULL, -- Supabase Storage URI or URL
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    processing_status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    processing_metadata JSONB DEFAULT '{}'::jsonb,
    analysis TEXT, -- Optional AI analysis of the asset
    analysis_type TEXT,
    analysis_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT current_timestamp,
    updated_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Indexes for assets
CREATE INDEX IF NOT EXISTS idx_assets_project_id ON assets(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_assets_user_id ON assets(user_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE INDEX IF NOT EXISTS idx_assets_processing_status ON assets(processing_status);

-- ============================================================================
-- STEP 3: RAG System Tables
-- ============================================================================

-- 3.1: Document Embeddings Table (for PDF/document RAG)
CREATE TABLE IF NOT EXISTS document_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL,
    user_id UUID NOT NULL,
    project_id UUID, -- Optional project reference
    document_type TEXT NOT NULL, -- 'pdf', 'docx', 'txt', etc.
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL, -- OpenAI text-embedding-3-small dimension
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Indexes for document_embeddings
CREATE INDEX IF NOT EXISTS idx_document_embeddings_asset ON document_embeddings(asset_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_user ON document_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_project ON document_embeddings(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector ON document_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 3.2: Message Embeddings Table (for chat message RAG)
CREATE TABLE IF NOT EXISTS message_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL,
    user_id UUID NOT NULL,
    project_id UUID, -- Optional project reference
    session_id UUID NOT NULL,
    embedding vector(1536) NOT NULL,
    content_snippet TEXT, -- First 500 chars of message
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Indexes for message_embeddings
CREATE INDEX IF NOT EXISTS idx_message_embeddings_message ON message_embeddings(message_id);
CREATE INDEX IF NOT EXISTS idx_message_embeddings_user ON message_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_message_embeddings_project ON message_embeddings(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_message_embeddings_session ON message_embeddings(session_id);
CREATE INDEX IF NOT EXISTS idx_message_embeddings_vector ON message_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 3.3: Global Knowledge Table (for extracted knowledge patterns)
CREATE TABLE IF NOT EXISTS global_knowledge (
    knowledge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL, -- 'character', 'plot', 'image_analysis', etc.
    pattern_type TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    example_text TEXT NOT NULL,
    description TEXT,
    quality_score NUMERIC(3,2) DEFAULT 0.7, -- 0.00 to 1.00
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT current_timestamp,
    updated_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Indexes for global_knowledge
CREATE INDEX IF NOT EXISTS idx_global_knowledge_category ON global_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_global_knowledge_pattern_type ON global_knowledge(pattern_type);
CREATE INDEX IF NOT EXISTS idx_global_knowledge_vector ON global_knowledge 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_global_knowledge_quality ON global_knowledge(quality_score DESC);

-- 3.4: Embedding Queue Table (for background processing)
CREATE TABLE IF NOT EXISTS embedding_queue (
    queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_type TEXT NOT NULL, -- 'message', 'document', 'knowledge'
    item_id UUID NOT NULL,
    user_id UUID NOT NULL,
    project_id UUID,
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT current_timestamp,
    processed_at TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0
);

-- Indexes for embedding_queue
CREATE INDEX IF NOT EXISTS idx_embedding_queue_status ON embedding_queue(status);
CREATE INDEX IF NOT EXISTS idx_embedding_queue_user ON embedding_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_embedding_queue_created ON embedding_queue(created_at);

-- ============================================================================
-- STEP 4: RPC Functions for RAG Similarity Search
-- ============================================================================

-- 4.1: Document Chunks Similarity Search
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
        1 - (de.embedding <=> query_embedding) AS similarity
    FROM document_embeddings de
    WHERE de.user_id = query_user_id
        AND (query_project_id IS NULL OR de.project_id = query_project_id)
        AND (1 - (de.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 4.2: Message Similarity Search
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
        1 - (me.embedding <=> query_embedding) AS similarity
    FROM message_embeddings me
    WHERE me.user_id = query_user_id
        AND (query_project_id IS NULL OR me.project_id = query_project_id)
        AND (1 - (me.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY me.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 4.3: Global Knowledge Similarity Search
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
        1 - (gk.embedding <=> query_embedding) AS similarity
    FROM global_knowledge gk
    WHERE gk.quality_score >= min_quality_score
        AND (1 - (gk.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY gk.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- STEP 5: Helper Functions for Session Management
-- ============================================================================

-- 5.1: Update Session Last Message Timestamp
CREATE OR REPLACE FUNCTION update_session_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions 
    SET last_message_at = NEW.created_at,
        updated_at = current_timestamp
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5.2: Trigger to Update Session Timestamp
DROP TRIGGER IF EXISTS trigger_update_session_last_message ON chat_messages;
CREATE TRIGGER trigger_update_session_last_message
    AFTER INSERT ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_last_message();

-- 5.3: Get User Sessions
CREATE OR REPLACE FUNCTION get_user_sessions(p_user_id UUID, p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    session_id UUID,
    project_id UUID,
    title TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    message_count BIGINT,
    last_message_preview TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.session_id,
        s.project_id,
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
    GROUP BY s.session_id, s.project_id, s.title, s.created_at, s.updated_at, s.last_message_at
    ORDER BY s.last_message_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 5.4: Get Session Messages
CREATE OR REPLACE FUNCTION get_session_messages(
    p_session_id UUID, 
    p_limit INTEGER DEFAULT 50, 
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    message_id UUID,
    role TEXT,
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cm.message_id,
        cm.role,
        cm.content,
        cm.metadata,
        cm.created_at
    FROM chat_messages cm
    WHERE cm.session_id = p_session_id
    ORDER BY cm.created_at ASC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 6: Authentication Helper Functions
-- ============================================================================

-- 6.1: Verify User Credentials
CREATE OR REPLACE FUNCTION verify_user_credentials(
    user_email TEXT,
    user_password_hash TEXT
) RETURNS TABLE(
    user_id UUID,
    email TEXT,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.user_id,
        u.email,
        u.display_name,
        u.avatar_url,
        u.created_at,
        u.updated_at
    FROM users u
    WHERE u.email = user_email 
    AND u.password_hash = user_password_hash
    AND u.password_hash IS NOT NULL;
END;
$$;

-- 6.2: Update User Password
CREATE OR REPLACE FUNCTION update_user_password(
    user_id_param UUID,
    new_password_hash TEXT
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE users 
    SET 
        password_hash = new_password_hash,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = user_id_param;
    
    RETURN FOUND;
END;
$$;

-- 6.3: Check if Email Exists
CREATE OR REPLACE FUNCTION email_exists(user_email TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN EXISTS(
        SELECT 1 FROM users 
        WHERE email = user_email
    );
END;
$$;

-- ============================================================================
-- STEP 7: Comments for Documentation
-- ============================================================================

COMMENT ON TABLE users IS 'User profiles and authentication data';
COMMENT ON TABLE sessions IS 'Chat sessions - project_id is optional UUID for grouping (NO dossier reference)';
COMMENT ON TABLE chat_messages IS 'Individual chat messages within sessions';
COMMENT ON TABLE user_projects IS 'Many-to-many relationship between users and projects (project_id is just a UUID)';
COMMENT ON TABLE assets IS 'File storage metadata - project_id is optional UUID reference';
COMMENT ON TABLE document_embeddings IS 'RAG: Document chunks with embeddings for semantic search';
COMMENT ON TABLE message_embeddings IS 'RAG: Chat message embeddings for context retrieval';
COMMENT ON TABLE global_knowledge IS 'RAG: Extracted knowledge patterns for cross-session learning';
COMMENT ON TABLE embedding_queue IS 'Queue for background embedding generation';

COMMENT ON FUNCTION get_similar_document_chunks IS 'RAG: Find similar document chunks using vector similarity';
COMMENT ON FUNCTION get_similar_user_messages IS 'RAG: Find similar chat messages using vector similarity';
COMMENT ON FUNCTION get_similar_global_knowledge IS 'RAG: Find similar knowledge patterns using vector similarity';
COMMENT ON FUNCTION get_user_sessions IS 'Get recent sessions for a user with message counts and previews';
COMMENT ON FUNCTION get_session_messages IS 'Get paginated messages for a specific session';

-- ============================================================================
-- NOTE: Row Level Security (RLS) is INTENTIONALLY DISABLED
-- All tables are accessible without RLS policies
-- ============================================================================

-- Verify setup
DO $$
BEGIN
    RAISE NOTICE '✅ Complete Supabase setup migration completed successfully!';
    RAISE NOTICE '✅ All tables created without RLS';
    RAISE NOTICE '✅ All RAG functions created';
    RAISE NOTICE '✅ No dossier tables or references';
END $$;

