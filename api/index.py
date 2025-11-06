"""
Minimal FastAPI with explicit error capture for Vercel
"""
import sys
import traceback
import os

# Force UTF-8 encoding and unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

def log_error(msg):
    """Log to both stdout and stderr so Vercel captures it"""
    print(msg, file=sys.stderr, flush=True)
    print(msg, flush=True)

log_error("=" * 60)
log_error("STARTING: Python process")
log_error(f"Python version: {sys.version}")
log_error(f"Python path: {sys.path}")
log_error("=" * 60)

try:
    log_error("Step 1: Importing FastAPI...")
    from fastapi import FastAPI
    log_error("Step 1: SUCCESS - FastAPI imported")
except Exception as e:
    log_error(f"Step 1: FAILED - {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

try:
    log_error("Step 2: Creating FastAPI app...")
    app = FastAPI()
    log_error("Step 2: SUCCESS - App created")
except Exception as e:
    log_error(f"Step 2: FAILED - {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

try:
    log_error("Step 3: Adding routes...")
    @app.get("/")
    def root():
        return {"status": "ok", "message": "Working"}
    
    @app.get("/health")
    def health():
        return {"status": "healthy"}
    log_error("Step 3: SUCCESS - Routes added")
except Exception as e:
    log_error(f"Step 3: FAILED - {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

try:
    log_error("Step 4: Exporting handler...")
    handler = app
    log_error("Step 4: SUCCESS - Handler exported")
except Exception as e:
    log_error(f"Step 4: FAILED - {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

log_error("=" * 60)
log_error("SUCCESS: All steps completed")
log_error("=" * 60)
