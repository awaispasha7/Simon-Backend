"""
Minimal FastAPI app - maximum error tolerance
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create app with minimal config
app = FastAPI()

# Add CORS - wrapped in try/except
try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except:
    pass  # Continue even if CORS fails

# Basic endpoint - NO imports, NO dependencies
@app.get("/")
async def root():
    return {"status": "ok", "message": "Simon Chatbot API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Load other routes ONLY if import succeeds
try:
    from app.api import auth
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
except Exception as e:
    print(f"Auth router skipped: {e}")

try:
    from app.api import simple_session_manager
    app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
except Exception as e:
    print(f"Session router skipped: {e}")

try:
    from app.api import simple_chat
    app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
except Exception as e:
    print(f"Chat router skipped: {e}")
