"""
Absolute minimal test - does Python even run?
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "message": "Minimal test working"}

@app.get("/health")
def health():
    return {"status": "healthy"}

handler = app
