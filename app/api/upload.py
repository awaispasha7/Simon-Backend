from fastapi import APIRouter, File, UploadFile, HTTPException, Header
from typing import List, Optional
import uuid
import os
import asyncio
from app.database.supabase import get_supabase_client
from dotenv import load_dotenv

# Try to import AI services with error handling
try:
    from app.ai.document_processor import document_processor
    DOCUMENT_PROCESSOR_AVAILABLE = True
    print(f"[UPLOAD] Document processor imported successfully")
    
    # Check if dependencies are available
    try:
        import PyPDF2
        print(f"[UPLOAD] PyPDF2 is available")
    except ImportError:
        print(f"[UPLOAD] WARNING: PyPDF2 is NOT installed - PDF processing will fail")
    
    try:
        import docx
        print(f"[UPLOAD] python-docx is available")
    except ImportError:
        print(f"[UPLOAD] WARNING: python-docx is NOT installed - DOCX processing will fail")
        
except Exception as e:
    print(f"[UPLOAD] ERROR: Document processor not available: {e}")
    import traceback
    print(traceback.format_exc())
    DOCUMENT_PROCESSOR_AVAILABLE = False
    document_processor = None

# Image analysis is now done during chat with full context (conversation history + RAG)
# No need for upload-time analysis - it's redundant and less accurate
IMAGE_ANALYSIS_AVAILABLE = False
image_analysis_service = None

router = APIRouter()
load_dotenv()

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file types
ALLOWED_EXTENSIONS = {
    'image': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
    'document': ['pdf', 'doc', 'docx', 'txt'],
    'video': ['mp4', 'mov', 'avi'],
    'script': ['pdf', 'txt', 'doc', 'docx']
}

def get_file_type(filename: str) -> str:
    """Determine file type based on extension"""
    extension = filename.lower().split('.')[-1]
    
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if extension in extensions:
            return file_type
    
    return 'other'

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Upload files to Supabase Storage and store metadata in assets table
    """
    print(f"[UPLOAD] Received {len(files)} file(s) for upload")
    print(f"[UPLOAD] Session ID: {x_session_id}")
    print(f"[UPLOAD] Project ID: {x_project_id}")
    print(f"[UPLOAD] User ID: {x_user_id}")
    
    # Debug: Check if we have the required data for guest users
    if not x_user_id and not x_session_id:
        print("[UPLOAD] Guest user with no session ID - this might cause issues")
    elif not x_user_id and x_session_id:
        print("[UPLOAD] Guest user with session ID - should work")
    elif x_user_id:
        print("[UPLOAD] Authenticated user - should work")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    uploaded_files = []
    supabase = get_supabase_client()
    
    # Create a bucket name for story assets
    bucket_name = "story-assets"
    
    try:
        for file in files:
            print(f"[UPLOAD] Processing file: {file.filename}")
            
            try:
                # Validate file size
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"File {file.filename} exceeds maximum size of 10MB"
                    )
                
                # Generate unique filename
                file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                
                # Determine file type
                file_type = get_file_type(file.filename)
                
                print(f"[UPLOAD] Uploading to Supabase Storage: {unique_filename}")

                # If Supabase is not configured, still process documents for RAG (critical feature)
                asset_id = str(uuid.uuid4())
                
                # Use single-user personal assistant IDs for RAG processing
                rag_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
                rag_project_id = uuid.UUID(x_project_id) if x_project_id else uuid.UUID("00000000-0000-0000-0000-000000000002")
                
                if not supabase:
                    print("[UPLOAD] Supabase not configured - storing minimal metadata, but will still process for RAG")
                
                # For documents, extract text immediately so it can be used in chat
                extracted_text = None
                if file_type in ['document', 'script'] and file_extension in ['pdf', 'docx', 'doc', 'txt'] and DOCUMENT_PROCESSOR_AVAILABLE:
                    print(f"[UPLOAD] Extracting text from document immediately (no Supabase): {file.filename}")
                    try:
                        from app.ai.document_processor import document_processor
                        extracted_text = await document_processor._extract_text(
                            content,
                            file.filename,
                            file.content_type or 'application/pdf'
                        )
                        if extracted_text:
                            print(f"[UPLOAD] Extracted {len(extracted_text)} chars from {file.filename}")
                        else:
                            print(f"[UPLOAD] No text extracted from {file.filename}")
                    except Exception as extract_error:
                        print(f"[UPLOAD] Error extracting text: {extract_error}")
                        import traceback
                        print(traceback.format_exc())
                
                # Create placeholder asset record without DB
                uploaded_file_data = {
                    "name": file.filename,
                    "size": len(content),
                    "url": f"local://{asset_id}",  # Placeholder URL
                    "type": file_type,
                    "asset_id": asset_id
                }
                
                # Include extracted text if available (for immediate use in chat)
                if extracted_text:
                    uploaded_file_data["extracted_text"] = extracted_text[:10000]  # Limit to 10k chars
                    print(f"[UPLOAD] Included extracted text in upload response for {file.filename}")
                
                uploaded_files.append(uploaded_file_data)
                
                # CRITICAL: Still process documents for RAG even without Supabase
                if file_type in ['document', 'script'] and file_extension in ['pdf', 'docx', 'doc', 'txt'] and DOCUMENT_PROCESSOR_AVAILABLE:
                    print(f"[UPLOAD] Processing document for RAG (no Supabase): {file.filename}")
                    try:
                        # Process document asynchronously for RAG ingestion
                        asyncio.create_task(
                            process_document_for_rag(
                                asset_id=uuid.UUID(asset_id),
                                user_id=rag_user_id,
                                project_id=rag_project_id,
                                file_content=content,
                                filename=file.filename,
                                content_type=file.content_type or 'application/octet-stream'
                            )
                        )
                        print(f"[UPLOAD] Document processing started for RAG: {file.filename}")
                    except Exception as rag_error:
                        print(f"[UPLOAD] Failed to start RAG processing: {rag_error}")
                        import traceback
                        print(traceback.format_exc())
                
                continue  # Skip Supabase storage operations
            
            # Upload to Supabase Storage
            try:
                # Upload file to storage
                storage_response = supabase.storage.from_(bucket_name).upload(
                    path=unique_filename,
                    file=content,
                    file_options={"content-type": file.content_type}
                )
                
                print(f"[UPLOAD] Upload response received")
                
                # Get URL - use signed URL for anonymous users, public URL for authenticated users
                # Signed URLs are valid for 1 year (31536000 seconds) to ensure they don't expire
                if not x_user_id:
                    # For anonymous users, create signed URL with long expiration
                    try:
                        print(f"[UPLOAD] Creating signed URL for anonymous user...")
                        signed_url_response = supabase.storage.from_(bucket_name).create_signed_url(
                            path=unique_filename,
                            expires_in=31536000  # 1 year in seconds
                        )
                        
                        # Handle different response formats from Supabase client
                        if isinstance(signed_url_response, dict):
                            public_url = signed_url_response.get('signedURL') or signed_url_response.get('signedUrl') or signed_url_response.get('url', '')
                            if not public_url and hasattr(signed_url_response, 'data'):
                                public_url = signed_url_response.data.get('signedURL') or signed_url_response.data.get('signedUrl') or signed_url_response.data.get('url', '')
                        elif isinstance(signed_url_response, str):
                            public_url = signed_url_response
                        elif hasattr(signed_url_response, 'signedURL'):
                            public_url = signed_url_response.signedURL
                        elif hasattr(signed_url_response, 'signedUrl'):
                            public_url = signed_url_response.signedUrl
                        else:
                            public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
                            print(f"[UPLOAD] Could not parse signed URL response, using public URL instead")
                        
                        if not public_url or public_url == '':
                            raise ValueError("Signed URL is empty after parsing")
                            
                        print(f"[UPLOAD] Signed URL created: {public_url[:50]}...")
                    except Exception as url_error:
                        print(f"[UPLOAD] Error creating signed URL: {url_error}")
                        import traceback
                        print(traceback.format_exc())
                        # Fallback to public URL if signed URL fails
                        try:
                            public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
                            print(f"[UPLOAD] Fallback to public URL: {public_url[:50]}...")
                        except Exception as fallback_error:
                            print(f"[UPLOAD] Fallback also failed: {fallback_error}")
                            raise HTTPException(status_code=500, detail=f"Failed to generate file URL: {str(url_error)}")
                else:
                    # For authenticated users, use public URL
                    public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
                    print(f"[UPLOAD] Public URL (authenticated user): {public_url[:50]}...")
                
                # Store metadata in assets table
                if x_project_id:
                    project_id = x_project_id
                    print(f"[UPLOAD] Using provided project ID: {project_id}")
                else:
                    project_id = "00000000-0000-0000-0000-000000000002"  # Default project ID for personal assistant
                    print(f"[UPLOAD] Using default project ID: {project_id}")
                
                # Use the actual user_id from the request, fallback to test ID if not provided
                user_id = x_user_id or "00000000-0000-0000-0000-000000000001"
                print(f"[UPLOAD] Using user_id: {user_id}")
                asset_id = str(uuid.uuid4())
                
                asset_record = {
                    "id": asset_id,
                    "project_id": project_id,
                    "type": file_type,
                    "uri": public_url,
                    "notes": f"Original filename: {file.filename}"
                }
                
                try:
                    db_response = supabase.table("assets").insert([asset_record]).execute()
                    if not db_response.data:
                        print(f"[UPLOAD] Warning: Failed to store asset metadata in database")
                except Exception as db_error:
                    print(f"[UPLOAD] Database error (non-fatal): {db_error}")
                    # Continue even if DB insert fails
                
                # Extract text from documents immediately for use in chat (even with Supabase)
                extracted_text = None
                if file_type in ['document', 'script'] and file_extension in ['pdf', 'docx', 'doc', 'txt']:
                    if not DOCUMENT_PROCESSOR_AVAILABLE:
                        print(f"[UPLOAD] Document processor not available - cannot extract text from {file.filename}")
                    elif not document_processor:
                        print(f"[UPLOAD] document_processor is None - cannot extract text from {file.filename}")
                    else:
                        print(f"[UPLOAD] Extracting text from document immediately (with Supabase): {file.filename}")
                        print(f"[UPLOAD] File size: {len(content)} bytes, Type: {file.content_type}")
                        try:
                            extracted_text = await document_processor._extract_text(
                                content,
                                file.filename,
                                file.content_type or 'application/pdf'
                            )
                            if extracted_text:
                                # Check if extraction returned an error message (dependencies missing)
                                if "not available" in extracted_text.lower() or "not installed" in extracted_text.lower():
                                    print(f"[UPLOAD] Dependencies missing: {extracted_text}")
                                    extracted_text = None
                                else:
                                    print(f"[UPLOAD] Extracted {len(extracted_text)} chars from {file.filename}")
                                    print(f"[UPLOAD] First 200 chars: {extracted_text[:200]}")
                            else:
                                print(f"[UPLOAD] No text extracted from {file.filename} - extraction returned empty")
                        except Exception as extract_error:
                            print(f"[UPLOAD] Error extracting text from {file.filename}: {extract_error}")
                            import traceback
                            print(f"[UPLOAD] Traceback: {traceback.format_exc()}")
                            extracted_text = None
                else:
                    print(f"[UPLOAD] Skipping text extraction - file_type={file_type}, extension={file_extension}, processor_available={DOCUMENT_PROCESSOR_AVAILABLE}")
                
                uploaded_file_data = {
                    "name": file.filename,
                    "size": len(content),
                    "url": public_url,
                    "type": file_type,
                    "asset_id": asset_id
                }
                
                # Include extracted text if available (for immediate use in chat)
                if extracted_text:
                    uploaded_file_data["extracted_text"] = extracted_text[:10000]  # Limit to 10k chars
                    print(f"[UPLOAD] Included extracted text in upload response for {file.filename}")
                
                uploaded_files.append(uploaded_file_data)
                
                print(f"[UPLOAD] File uploaded successfully: {file.filename}")
                
                # Process document for RAG if it's a text-based document
                if file_type in ['document', 'script'] and file_extension in ['pdf', 'docx', 'doc', 'txt'] and DOCUMENT_PROCESSOR_AVAILABLE:
                    print(f"[UPLOAD] Processing document for RAG: {file.filename}")
                    
                    # Use single-user personal assistant IDs for RAG (consistent with chat)
                    rag_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
                    rag_project_id = uuid.UUID(project_id)
                    
                    # Process document asynchronously for RAG ingestion
                    try:
                        asyncio.create_task(
                            process_document_for_rag(
                                asset_id=uuid.UUID(asset_id),
                                user_id=rag_user_id,
                                project_id=rag_project_id,
                                file_content=content,
                                filename=file.filename,
                                content_type=file.content_type or 'application/octet-stream'
                            )
                        )
                        print(f"[UPLOAD] Document processing started for RAG: {file.filename}")
                    except Exception as rag_task_error:
                        print(f"[UPLOAD] Failed to start RAG processing task (non-fatal): {rag_task_error}")
                        # Continue even if RAG task fails
            
            except Exception as storage_error:
                print(f"[UPLOAD] Storage error for {file.filename}: {str(storage_error)}")
                import traceback
                print(traceback.format_exc())
                # Don't fail the entire upload - add error info to response
                uploaded_files.append({
                    "name": file.filename or "unknown",
                    "size": len(content) if 'content' in locals() else 0,
                    "url": None,
                    "type": file_type if 'file_type' in locals() else "unknown",
                    "asset_id": None,
                    "error": f"Upload failed: {str(storage_error)}"
                })
                print(f"[UPLOAD] Added file with error to response (non-fatal)")
            
            except Exception as file_error:
                print(f"[UPLOAD] Error processing file {file.filename if hasattr(file, 'filename') else 'unknown'}: {str(file_error)}")
                import traceback
                print(traceback.format_exc())
                # Add error to response but don't fail entire upload
                uploaded_files.append({
                    "name": file.filename if hasattr(file, 'filename') else "unknown",
                    "size": 0,
                    "url": None,
                    "type": "unknown",
                    "asset_id": None,
                    "error": f"Processing failed: {str(file_error)}"
                })
    
    except Exception as e:
        print(f"[UPLOAD] Upload error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        # Return partial success if we have any files
        if uploaded_files:
            return {
                "success": True,
                "files": uploaded_files,
                "count": len(uploaded_files),
                "warning": f"Some files may have failed: {str(e)}"
            }
        raise HTTPException(status_code=500, detail=str(e))
    
    return {
        "success": True,
        "files": uploaded_files,
        "count": len(uploaded_files)
    }


async def process_document_for_rag(
    asset_id: uuid.UUID,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    file_content: bytes,
    filename: str,
    content_type: str
):
    """
    Background task to process uploaded document for RAG
    
    Args:
        asset_id: ID of the asset
        user_id: ID of the user
        project_id: ID of the project
        file_content: Raw file content
        filename: Original filename
        content_type: MIME type
    """
    try:
        print(f"[RAG] Starting RAG processing for document: {filename}")
        
        result = await document_processor.process_document(
            asset_id=asset_id,
            user_id=user_id,
            project_id=project_id,
            file_content=file_content,
            filename=filename,
            content_type=content_type
        )
        
        if result["success"]:
            print(f"[RAG] RAG processing completed for {filename}: {result['embeddings_created']} embeddings created")
        else:
            print(f"[RAG] RAG processing failed for {filename}: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"[RAG] Error in background RAG processing for {filename}: {e}")
        import traceback
        print(traceback.format_exc())

