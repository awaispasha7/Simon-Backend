"""
Minimal FastAPI for Vercel - correct handler export
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "message": "Working"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Vercel expects 'handler' to be the ASGI app
handler = app
