"""
Vercel entry point
"""
import traceback

print("=" * 60)
print("Starting Vercel function...")
print("=" * 60)

try:
    print("Importing app.main...")
    from app.main import app
    print("✅ Import successful")
    handler = app
except Exception as e:
    print(f"❌ Import failed: {type(e).__name__}: {e}")
    traceback.print_exc()
    
    # Create fallback app
    print("Creating fallback app...")
    from fastapi import FastAPI
    fallback_app = FastAPI()
    
    @fallback_app.get("/")
    async def root():
        return {"error": "Import failed", "details": str(e)}
    
    @fallback_app.get("/health")
    async def health():
        return {"status": "error", "message": "Main app failed to import"}
    
    handler = fallback_app
    print("✅ Fallback app created")

print("=" * 60)
