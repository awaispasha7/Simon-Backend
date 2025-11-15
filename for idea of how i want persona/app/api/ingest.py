"""
Bulk PDF Ingestion API
High-priority endpoint for ingesting client PDFs into RAG system
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Header
from typing import List, Optional
import os
import asyncio
from uuid import UUID, uuid4
from ..database.supabase import get_supabase_client
from ..ai.document_processor import document_processor

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/bulk-pdfs")
async def bulk_ingest_pdfs(
    files: List[UploadFile] = File(...),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID")
):
    """
    Bulk ingest PDFs from client into RAG system
    High-priority endpoint for contextual responses
    
    Args:
        files: List of PDF files to ingest
        x_user_id: Optional user ID (for multi-user setups)
        x_project_id: Optional project ID (for project isolation)
    
    Returns:
        Processing results for each file
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    print(f"📚 Bulk PDF ingestion: {len(files)} file(s)")
    
    # Use default user/project IDs if not provided (for MVP)
    user_id = UUID(x_user_id) if x_user_id else UUID("00000000-0000-0000-0000-000000000001")
    project_id = UUID(x_project_id) if x_project_id else UUID("00000000-0000-0000-0000-000000000002")
    
    supabase = get_supabase_client()
    results = []
    
    for file in files:
        file_result = {
            "filename": file.filename,
            "success": False,
            "chunks_created": 0,
            "error": None
        }
        
        try:
            # Validate PDF
            if not file.filename.lower().endswith('.pdf'):
                file_result["error"] = "Only PDF files are supported"
                results.append(file_result)
                continue
            
            # Read file content
            content = await file.read()
            if len(content) == 0:
                file_result["error"] = "File is empty"
                results.append(file_result)
                continue
            
            print(f"📄 Processing: {file.filename} ({len(content)} bytes)")
            
            # Create asset record (even without Supabase, we need asset_id)
            asset_id = uuid4()
            
            if supabase:
                asset_record = {
                    "id": str(asset_id),
                    "project_id": str(project_id),
                    "type": "document",
                    "uri": f"ingested://{file.filename}",  # Placeholder URI
                    "notes": f"Bulk ingested PDF: {file.filename}",
                    "processing_status": "processing"
                }
                try:
                    supabase.table("assets").insert([asset_record]).execute()
                    print(f"✅ Asset record created: {asset_id}")
                except Exception as e:
                    print(f"⚠️ Failed to create asset record (continuing anyway): {e}")
            
            # Process document for RAG (this is the critical part)
            try:
                processing_result = await document_processor.process_document(
                    asset_id=asset_id,
                    user_id=user_id,
                    project_id=project_id,
                    file_content=content,
                    filename=file.filename,
                    content_type="application/pdf"
                )
                
                if processing_result.get("success"):
                    file_result["success"] = True
                    file_result["chunks_created"] = processing_result.get("embeddings_created", 0)
                    file_result["total_text_length"] = processing_result.get("total_text_length", 0)
                    print(f"✅ Successfully ingested {file.filename}: {file_result['chunks_created']} chunks created")
                else:
                    file_result["error"] = processing_result.get("error", "Processing failed")
                    print(f"❌ Failed to ingest {file.filename}: {file_result['error']}")
                    
            except Exception as process_error:
                file_result["error"] = str(process_error)
                print(f"❌ Error processing {file.filename}: {process_error}")
                import traceback
                print(traceback.format_exc())
            
        except Exception as e:
            file_result["error"] = str(e)
            print(f"❌ Error with {file.filename}: {e}")
            import traceback
            print(traceback.format_exc())
        
        results.append(file_result)
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    total_chunks = sum(r["chunks_created"] for r in results if r["success"])
    
    return {
        "success": True,
        "files_processed": len(results),
        "files_successful": successful,
        "files_failed": len(results) - successful,
        "total_chunks_created": total_chunks,
        "results": results
    }

@router.get("/status")
async def ingestion_status():
    """Get ingestion status and statistics"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return {
                "status": "no_database",
                "message": "Supabase not configured - ingestion will work but metadata won't be stored"
            }
        
        # Get document embeddings count
        try:
            embeddings_result = supabase.table("document_embeddings").select("embedding_id", count="exact").execute()
            embedding_count = embeddings_result.count if hasattr(embeddings_result, 'count') else 0
        except:
            embedding_count = 0
        
        # Get assets count
        try:
            assets_result = supabase.table("assets").select("id", count="exact").execute()
            asset_count = assets_result.count if hasattr(assets_result, 'count') else 0
        except:
            asset_count = 0
        
        # Get embeddings by user
        try:
            user_embeddings = supabase.table("document_embeddings").select("user_id").execute()
            user_counts = {}
            for row in user_embeddings.data:
                user_id = row.get('user_id')
                user_counts[user_id] = user_counts.get(user_id, 0) + 1
        except:
            user_counts = {}
        
        # Get embeddings by document type
        try:
            type_result = supabase.table("document_embeddings").select("document_type").execute()
            type_counts = {}
            for row in type_result.data:
                doc_type = row.get('document_type', 'unknown')
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        except:
            type_counts = {}
        
        return {
            "status": "active",
            "embeddings_count": embedding_count,
            "assets_count": asset_count,
            "embeddings_by_user": user_counts,
            "embeddings_by_type": type_counts,
            "rag_enabled": True
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/debug/embeddings")
async def debug_embeddings(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    limit: int = 10
):
    """Debug endpoint to view stored embeddings"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return {
                "error": "Supabase not configured"
            }
        
        user_id = x_user_id if x_user_id else None
        
        query = supabase.table("document_embeddings").select("*")
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.limit(limit).execute()
        
        # Format for readability
        embeddings = []
        for row in result.data:
            embeddings.append({
                "embedding_id": row.get("embedding_id"),
                "asset_id": row.get("asset_id"),
                "user_id": row.get("user_id"),
                "project_id": row.get("project_id"),
                "document_type": row.get("document_type"),
                "chunk_index": row.get("chunk_index"),
                "chunk_text_preview": row.get("chunk_text", "")[:200] + "..." if len(row.get("chunk_text", "")) > 200 else row.get("chunk_text", ""),
                "chunk_text_length": len(row.get("chunk_text", "")),
                "has_embedding": row.get("embedding") is not None,
                "embedding_dimension": len(row.get("embedding", [])) if row.get("embedding") else 0,
                "created_at": row.get("created_at")
            })
        
        return {
            "success": True,
            "count": len(embeddings),
            "embeddings": embeddings
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

