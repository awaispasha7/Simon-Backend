"""
Audio Transcription API
Handles audio file uploads and converts them to text using OpenAI Whisper
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import openai
import os
import tempfile
import uuid
from dotenv import load_dotenv

router = APIRouter()
load_dotenv()

@router.post("/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribe audio file to text using OpenAI Whisper API
    """
    try:
        print(f"🎤 Received audio file: {audio_file.filename}")
        print(f"🎤 Content type: {audio_file.content_type}")
        print(f"🎤 File size: {audio_file.size if hasattr(audio_file, 'size') else 'unknown'}")
        
        # Validate that we received a file
        if not audio_file.filename and not audio_file.content_type:
            print("❌ No file received or invalid file")
            raise HTTPException(status_code=400, detail="No audio file received")
        
        # Validate file type - be more lenient with webm files
        if audio_file.content_type:
            if not (audio_file.content_type.startswith('audio/') or 
                   audio_file.content_type == 'video/webm' or 
                   audio_file.content_type == 'audio/webm'):
                print(f"❌ Invalid content type: {audio_file.content_type}")
                raise HTTPException(status_code=400, detail=f"File must be an audio file. Received: {audio_file.content_type}")
        else:
            # If no content type, check filename extension
            if audio_file.filename:
                valid_extensions = ['.wav', '.mp3', '.m4a', '.webm', '.ogg', '.flac']
                if not any(audio_file.filename.lower().endswith(ext) for ext in valid_extensions):
                    print(f"❌ Invalid file extension: {audio_file.filename}")
                    raise HTTPException(status_code=400, detail=f"File must be an audio file. Received: {audio_file.filename}")
        
        # Validate file size (max 25MB for Whisper)
        MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
        file_content = await audio_file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Audio file too large. Max size is 25MB.")
        
        print(f"🎤 File content size: {len(file_content)} bytes")
        
        # Determine file extension from filename or content type
        file_extension = '.webm'  # Default
        if audio_file.filename:
            if audio_file.filename.lower().endswith('.webm'):
                file_extension = '.webm'
            elif audio_file.filename.lower().endswith('.mp3'):
                file_extension = '.mp3'
            elif audio_file.filename.lower().endswith('.wav'):
                file_extension = '.wav'
            elif audio_file.filename.lower().endswith('.m4a'):
                file_extension = '.m4a'
        
        # Create temporary file for Whisper API (preserve original format)
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        print(f"🎤 Created temp file: {temp_file_path} with extension {file_extension}")
        
        try:
            # Check if OpenAI API key is available
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("❌ OpenAI API key not found")
                raise HTTPException(status_code=500, detail="OpenAI API key not configured")
            
            # Initialize OpenAI client
            openai_client = openai.OpenAI(api_key=api_key)
            
            # Transcribe using Whisper
            print("🎤 Sending audio to OpenAI Whisper...")
            with open(temp_file_path, 'rb') as audio_file_obj:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file_obj,
                    response_format="text"
                )
            
            print(f"✅ Transcription successful: '{transcript[:100]}...'")
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return JSONResponse(content={
                "transcript": transcript.strip(),
                "success": True,
                "model_used": "whisper-1",
                "file_name": audio_file.filename
            })
            
        except openai.APIError as e:
            print(f"❌ OpenAI API error: {e}")
            print(f"❌ Error type: {type(e)}")
            print(f"❌ Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            print(f"❌ Error type: {type(e)}")
            print(f"❌ Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in transcribe endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/transcribe/health")
async def transcribe_health():
    """
    Health check for transcription service
    """
    try:
        # Check if OpenAI API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return JSONResponse(content={
                "status": "error",
                "message": "OpenAI API key not configured"
            }, status_code=500)
        
        return JSONResponse(content={
            "status": "healthy",
            "message": "Transcription service ready",
            "model": "whisper-1"
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }, status_code=500)
