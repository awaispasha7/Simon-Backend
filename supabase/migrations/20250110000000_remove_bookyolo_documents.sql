-- Migration: Remove BookYolo test documents
-- This removes all BookYolo-related documents that were used for testing PDF upload/ingestion

-- Step 1: Find and delete document embeddings for BookYolo documents
-- These are identified by filename in metadata or content
DO $$
DECLARE
    deleted_embeddings_count INTEGER;
    deleted_assets_count INTEGER;
    asset_ids_to_delete UUID[];
BEGIN
    -- Get asset IDs that need to be deleted
    SELECT ARRAY_AGG(DISTINCT asset_id::uuid) INTO asset_ids_to_delete
    FROM document_embeddings
    WHERE metadata->>'filename' ILIKE '%BookYolo%'
       OR metadata->>'filename' ILIKE '%Specifications_Final%'
       OR chunk_text ILIKE '%BookYolo%'
       OR chunk_text ILIKE '%BOOKYOLO%';
    
    -- Delete document embeddings
    DELETE FROM document_embeddings
    WHERE metadata->>'filename' ILIKE '%BookYolo%'
       OR metadata->>'filename' ILIKE '%Specifications_Final%'
       OR chunk_text ILIKE '%BookYolo%'
       OR chunk_text ILIKE '%BOOKYOLO%';
    
    GET DIAGNOSTICS deleted_embeddings_count = ROW_COUNT;
    
    -- Step 2: Delete assets for BookYolo documents
    IF asset_ids_to_delete IS NOT NULL AND array_length(asset_ids_to_delete, 1) > 0 THEN
        DELETE FROM assets
        WHERE id = ANY(asset_ids_to_delete);
        
        GET DIAGNOSTICS deleted_assets_count = ROW_COUNT;
    ELSE
        deleted_assets_count := 0;
    END IF;
    
    -- Step 3: Also delete any remaining assets by checking notes/uri
    DELETE FROM assets
    WHERE (notes ILIKE '%BookYolo%' OR notes ILIKE '%Specifications_Final%'
           OR uri ILIKE '%BookYolo%' OR uri ILIKE '%Specifications_Final%')
       AND id != ALL(COALESCE(asset_ids_to_delete, ARRAY[]::uuid[]));
    
    GET DIAGNOSTICS deleted_assets_count = deleted_assets_count + ROW_COUNT;
    
    RAISE NOTICE 'Cleaned up BookYolo documents: % embeddings deleted, % assets deleted', 
        deleted_embeddings_count, deleted_assets_count;
END $$;

