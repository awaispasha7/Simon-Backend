"""
Vercel Serverless Function Entry Point
This file is used by Vercel to serve the FastAPI application
"""
import sys
import traceback

try:
    print("=" * 50)
    print("🔧 Initializing FastAPI application for Vercel...")
    print("=" * 50)
    
    from app.main import app
    
    print("✅ FastAPI app imported successfully")
    print("=" * 50)
    
    # Export the app for Vercel
    handler = app
    
except Exception as e:
    print(f"❌ CRITICAL ERROR: Failed to import app: {e}")
    print(f"❌ Traceback: {traceback.format_exc()}")
    sys.exit(1)
