"""
Vercel entry point - absolute minimal
"""
try:
    from app.main import app
    handler = app
except Exception as e:
    # Create minimal app if import fails
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"error": "Import failed", "message": str(e)}
    
    handler = app
