"""
Absolute minimal test - try different handler export
"""
try:
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"status": "ok", "message": "Test"}
    
    @app.get("/health")
    def health():
        return {"status": "healthy"}
    
    # Try exporting as handler function
    def handler(request):
        return app(request)
    
except Exception as e:
    # If FastAPI fails, create minimal fallback
    def handler(request):
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"status": "error", "message": "' + str(e) + '"}'
        }
