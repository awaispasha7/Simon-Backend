"""
Vercel Serverless Function Entry Point
This file is used by Vercel to serve the FastAPI application
"""
import sys
import traceback

try:
    print("=" * 60)
    print("🔧 Vercel: Initializing FastAPI application...")
    print("=" * 60)
    
    # Import app - this should never crash
    from app.main import app
    
    print("✅ FastAPI app imported successfully")
    print("=" * 60)
    
    # Export for Vercel
    handler = app
    
except Exception as e:
    # Log error but don't exit - let Vercel handle it
    print(f"❌ CRITICAL ERROR importing app: {type(e).__name__}: {e}")
    print(f"❌ Traceback:")
    traceback.print_exc()
    # Don't sys.exit - let it fail gracefully
    raise
