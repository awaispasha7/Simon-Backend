"""
LangSmith Configuration and Callback Handlers
Provides automatic tracing for OpenAI API calls and manual tracing utilities
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Try to import LangSmith with graceful degradation
try:
    from langsmith import Client, traceable
    from langsmith.wrappers import wrap_openai
    from langsmith.run_helpers import tracing_context
    LANGSMITH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: LangSmith not available: {e}")
    LANGSMITH_AVAILABLE = False
    traceable = None
    wrap_openai = None
    tracing_context = None
    Client = None

# LangSmith configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "simon-chatbot")
LANGSMITH_WORKSPACE_ID = os.getenv("LANGSMITH_WORKSPACE_ID")  # Required for org-scoped API keys
LANGSMITH_TRACING_V2 = os.getenv("LANGSMITH_TRACING_V2", "true").lower() == "true"

# Global LangSmith client instance
_langsmith_client = None


def get_langsmith_client() -> Optional[Any]:
    """Get or create LangSmith client instance"""
    global _langsmith_client
    
    if not LANGSMITH_AVAILABLE:
        return None
    
    if not LANGSMITH_API_KEY:
        return None
    
    if _langsmith_client is None:
        try:
            # For org-scoped API keys, workspace_id must be set as environment variable
            # The Client reads from environment variables, not constructor parameters
            if LANGSMITH_WORKSPACE_ID:
                os.environ["LANGSMITH_WORKSPACE_ID"] = LANGSMITH_WORKSPACE_ID
            
            _langsmith_client = Client(api_key=LANGSMITH_API_KEY)
            print("[OK] LangSmith client initialized")
            if LANGSMITH_WORKSPACE_ID:
                print(f"[OK] Using workspace: {LANGSMITH_WORKSPACE_ID}")
        except Exception as e:
            print(f"[WARN] Failed to initialize LangSmith client: {e}")
            return None
    
    return _langsmith_client


def is_langsmith_enabled() -> bool:
    """Check if LangSmith is enabled and available"""
    return LANGSMITH_AVAILABLE and LANGSMITH_API_KEY is not None


def wrap_openai_client(client: Any) -> Any:
    """
    Wrap OpenAI client with LangSmith callbacks for automatic tracing
    
    Args:
        client: OpenAI client instance (OpenAI or AsyncOpenAI)
        
    Returns:
        Wrapped client with LangSmith tracing enabled
    """
    if not is_langsmith_enabled():
        return client
    
    try:
        if wrap_openai is None:
            return client
        
        # Set project name and workspace via environment variable for wrap_openai
        # wrap_openai reads from LANGSMITH_PROJECT and LANGSMITH_WORKSPACE_ID env vars automatically
        import os
        original_project = os.getenv("LANGSMITH_PROJECT")
        original_workspace = os.getenv("LANGSMITH_WORKSPACE_ID")
        
        os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
        if LANGSMITH_WORKSPACE_ID:
            os.environ["LANGSMITH_WORKSPACE_ID"] = LANGSMITH_WORKSPACE_ID
        
        try:
            # wrap_openai doesn't take project_name parameter directly
            # It reads from LANGSMITH_PROJECT and LANGSMITH_WORKSPACE_ID environment variables
            wrapped = wrap_openai(client)
            print("[OK] OpenAI client wrapped with LangSmith tracing")
            return wrapped
        finally:
            # Restore original values if they were set
            if original_project:
                os.environ["LANGSMITH_PROJECT"] = original_project
            elif "LANGSMITH_PROJECT" in os.environ:
                del os.environ["LANGSMITH_PROJECT"]
            
            if original_workspace:
                os.environ["LANGSMITH_WORKSPACE_ID"] = original_workspace
            elif "LANGSMITH_WORKSPACE_ID" in os.environ and not LANGSMITH_WORKSPACE_ID:
                del os.environ["LANGSMITH_WORKSPACE_ID"]
                
    except Exception as e:
        print(f"[WARN] Failed to wrap OpenAI client with LangSmith: {e}")
        return client


def create_trace(
    name: str,
    run_type: str = "chain",
    tags: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Create a manual trace for non-OpenAI operations
    
    Args:
        name: Name of the trace
        run_type: Type of run (chain, tool, llm, etc.)
        tags: List of tags for filtering
        metadata: Additional metadata
        
    Returns:
        Trace context manager
    """
    if not is_langsmith_enabled():
        # Return a no-op context manager
        from contextlib import nullcontext
        return nullcontext()
    
    try:
        if tracing_context is None:
            from contextlib import nullcontext
            return nullcontext()
        
        # Ensure workspace_id is set as environment variable (required for org-scoped API keys)
        # tracing_context reads from environment variables, not parameters
        if LANGSMITH_WORKSPACE_ID:
            os.environ["LANGSMITH_WORKSPACE_ID"] = LANGSMITH_WORKSPACE_ID
        
        # Build kwargs for tracing_context
        trace_kwargs = {
            "project_name": LANGSMITH_PROJECT,
            "name": name,
            "run_type": run_type,
            "tags": tags or [],
            "metadata": metadata or {}
        }
        
        return tracing_context(**trace_kwargs)
    except Exception as e:
        print(f"[WARN] Failed to create LangSmith trace: {e}")
        from contextlib import nullcontext
        return nullcontext()


def trace_function(
    name: Optional[str] = None,
    run_type: str = "chain",
    tags: Optional[list] = None
):
    """
    Decorator for tracing functions with LangSmith
    
    Args:
        name: Name of the trace (defaults to function name)
        run_type: Type of run
        tags: List of tags
        
    Returns:
        Decorated function with tracing
    """
    if not is_langsmith_enabled() or traceable is None:
        # Return a no-op decorator
        def noop_decorator(func):
            return func
        return noop_decorator
    
    try:
        # Ensure workspace_id is set as environment variable (required for org-scoped API keys)
        # traceable reads from environment variables, not parameters
        if LANGSMITH_WORKSPACE_ID:
            os.environ["LANGSMITH_WORKSPACE_ID"] = LANGSMITH_WORKSPACE_ID
        
        # Build kwargs for traceable
        traceable_kwargs = {
            "name": name,
            "project_name": LANGSMITH_PROJECT,
            "run_type": run_type,
            "tags": tags or []
        }
        
        return traceable(**traceable_kwargs)
    except Exception as e:
        print(f"[WARN] Failed to create LangSmith trace decorator: {e}")
        def noop_decorator(func):
            return func
        return noop_decorator


# Initialize on module load
if is_langsmith_enabled():
    get_langsmith_client()
    print(f"[OK] LangSmith monitoring enabled (project: {LANGSMITH_PROJECT})")
else:
    print("[WARN] LangSmith monitoring disabled (set LANGSMITH_API_KEY to enable)")

