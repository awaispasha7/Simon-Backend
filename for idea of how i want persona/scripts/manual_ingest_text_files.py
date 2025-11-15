"""
Manually ingest the two text files for RAG
This ensures they're properly processed and stored
"""

import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.ai.document_processor import document_processor

async def ingest_file(file_path: str, filename: str):
    """Ingest a single text file"""
    print(f"\n{'='*60}")
    print(f"Processing: {filename}")
    print(f"{'='*60}")
    
    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    
    # Create asset ID
    asset_id = uuid4()
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    project_id = UUID("00000000-0000-0000-0000-000000000002")
    
    print(f"Asset ID: {asset_id}")
    print(f"User ID: {user_id}")
    print(f"Project ID: {project_id}")
    
    # Process document
    print("\nProcessing document for RAG...")
    try:
        result = await document_processor.process_document(
            asset_id=asset_id,
            user_id=user_id,
            project_id=project_id,
            file_content=content.encode('utf-8'),
            filename=filename,
            content_type="text/plain"
        )
        
        if result.get("success"):
            chunks = result.get("embeddings_created", 0)
            text_length = result.get("total_text_length", 0)
            print(f"\n✅ SUCCESS!")
            print(f"   Chunks created: {chunks}")
            print(f"   Text length: {text_length} characters")
            return True
        else:
            error = result.get("error", "Unknown error")
            print(f"\n❌ FAILED: {error}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def main():
    """Main function"""
    print("="*60)
    print("MANUAL TEXT FILE INGESTION")
    print("="*60)
    
    # Get script directory
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    
    # File paths
    files = [
        (backend_dir / "simon_personal_description.txt", "simon_personal_description.txt"),
        (backend_dir / "document_explanation_guide.txt", "document_explanation_guide.txt")
    ]
    
    results = []
    for file_path, filename in files:
        if not file_path.exists():
            print(f"\n❌ File not found: {file_path}")
            results.append(False)
            continue
        
        success = await ingest_file(str(file_path), filename)
        results.append(success)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Files processed: {successful}/{total}")
    
    if successful == total:
        print("\n✅ All files ingested successfully!")
        print("\nNext steps:")
        print("1. Wait 5-10 seconds for embeddings to be stored")
        print("2. Test with: 'What's my tone?'")
        print("3. Test with: 'Tell me about yourself'")
    else:
        print("\n⚠️ Some files failed to ingest")
        print("Check the error messages above")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

