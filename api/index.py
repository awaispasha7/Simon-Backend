"""
Ultra minimal - test if Vercel Python works at all
"""
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Try Mangum adapter for AWS Lambda/Vercel
try:
    handler = Mangum(app)
except:
    # Fallback to direct app
    handler = app
