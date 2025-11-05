-- ============================================================================
-- RAG System Setup Migration
-- Creates all necessary tables, functions, and indexes for RAG functionality
-- ============================================================================

-- Step 1: Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create document_embeddings table (for PDF/document RAG)
CREATE TABLE IF NOT EXISTS document_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL,
    user_id UUID NOT NULL,
    project_id UUID,
    document_type TEXT NOT NULL, -- 'pdf', 'docx', 'txt', etc.
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL, -- OpenAI text-embedding-3-small dimension
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Create indexes for document_embeddings
CREATE INDEX IF NOT EXISTS idx_document_embeddings_asset ON document_embeddings(asset_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_user ON document_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_project ON document_embeddings(project_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector ON document_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Step 3: Create message_embeddings table (for chat message RAG)
CREATE TABLE IF NOT EXISTS message_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL,
    user_id UUID NOT NULL,
    project_id UUID,
    session_id UUID NOT NULL,
    embedding vector(1536) NOT NULL,
    content_snippet TEXT, -- First 500 chars of message
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Create indexes for message_embeddings
CREATE INDEX IF NOT EXISTS idx_message_embeddings_message ON message_embeddings(message_id);
CREATE INDEX IF NOT EXISTS idx_message_embeddings_user ON message_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_message_embeddings_project ON message_embeddings(project_id);
CREATE INDEX IF NOT EXISTS idx_message_embeddings_session ON message_embeddings(session_id);
CREATE INDEX IF NOT EXISTS idx_message_embeddings_vector ON message_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Step 4: Create global_knowledge table (for extracted knowledge patterns)
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

-- Create indexes for global_knowledge
CREATE INDEX IF NOT EXISTS idx_global_knowledge_category ON global_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_global_knowledge_pattern_type ON global_knowledge(pattern_type);
CREATE INDEX IF NOT EXISTS idx_global_knowledge_vector ON global_knowledge 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_global_knowledge_quality ON global_knowledge(quality_score DESC);

-- Step 5: Create embedding_queue table (for background processing)
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

-- Create indexes for embedding_queue
CREATE INDEX IF NOT EXISTS idx_embedding_queue_status ON embedding_queue(status);
CREATE INDEX IF NOT EXISTS idx_embedding_queue_user ON embedding_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_embedding_queue_created ON embedding_queue(created_at);

-- Step 6: Update assets table (add columns if they don't exist)
DO $$ 
BEGIN
    -- Add processing_status column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'assets' AND column_name = 'processing_status') THEN
        ALTER TABLE assets ADD COLUMN processing_status TEXT DEFAULT 'pending';
    END IF;
    
    -- Add processing_metadata column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'assets' AND column_name = 'processing_metadata') THEN
        ALTER TABLE assets ADD COLUMN processing_metadata JSONB DEFAULT '{}'::jsonb;
    END IF;
    
    -- Add user_id column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'assets' AND column_name = 'user_id') THEN
        ALTER TABLE assets ADD COLUMN user_id UUID;
    END IF;
    
    -- Add updated_at column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'assets' AND column_name = 'updated_at') THEN
        ALTER TABLE assets ADD COLUMN updated_at TIMESTAMPTZ DEFAULT current_timestamp;
    END IF;
END $$;

-- Step 7: Create RPC function for document chunk similarity search
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

-- Step 8: Create RPC function for message similarity search
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

-- Step 9: Create RPC function for global knowledge similarity search
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

-- Step 10: Set up Row Level Security (RLS) policies

-- For MVP: Disable RLS to allow easy access (you can enable later for production)
-- Uncomment the lines below if you want to enable RLS

-- Enable RLS on all tables (commented for MVP)
-- ALTER TABLE document_embeddings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE message_embeddings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE global_knowledge ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE embedding_queue ENABLE ROW LEVEL SECURITY;

-- Document embeddings policies (commented for MVP - enable when needed)
-- CREATE POLICY "Users can view their own document embeddings"
--     ON document_embeddings FOR SELECT
--     USING (true);  -- For MVP: allow all, restrict later

-- CREATE POLICY "Users can insert their own document embeddings"
--     ON document_embeddings FOR INSERT
--     WITH CHECK (true);  -- For MVP: allow all, restrict later

-- Message embeddings policies (commented for MVP - enable when needed)
-- CREATE POLICY "Users can view their own message embeddings"
--     ON message_embeddings FOR SELECT
--     USING (true);

-- CREATE POLICY "Users can insert their own message embeddings"
--     ON message_embeddings FOR INSERT
--     WITH CHECK (true);

-- Global knowledge: public read (shared knowledge base)
-- CREATE POLICY "Public can view global knowledge"
--     ON global_knowledge FOR SELECT
--     USING (true);

-- Embedding queue policies (commented for MVP - enable when needed)
-- CREATE POLICY "Users can view their own embedding queue items"
--     ON embedding_queue FOR SELECT
--     USING (true);

-- CREATE POLICY "Users can insert their own embedding queue items"
--     ON embedding_queue FOR INSERT
--     WITH CHECK (true);

-- NOTE: For production, you should enable RLS and create proper user-based policies
-- This MVP setup allows full access to simplify initial testing

-- Step 11: Create storage bucket for assets (if not exists)
-- Note: This requires Supabase Storage API, so we'll handle it in the setup script
-- For now, document that the bucket needs to be created manually

-- ============================================================================
-- Verification queries (run these after migration to verify setup)
-- ============================================================================

-- Check extension is enabled
-- SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check tables exist
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' 
-- AND table_name IN ('document_embeddings', 'message_embeddings', 'global_knowledge', 'embedding_queue');

-- Check indexes exist
-- SELECT indexname FROM pg_indexes 
-- WHERE tablename IN ('document_embeddings', 'message_embeddings', 'global_knowledge');

-- Check functions exist
-- SELECT routine_name FROM information_schema.routines 
-- WHERE routine_schema = 'public' 
-- AND routine_name IN ('get_similar_document_chunks', 'get_similar_user_messages', 'get_similar_global_knowledge');

