"""
Quick test to verify LangSmith connection and configuration
Run this to diagnose why traces aren't appearing
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

print("=" * 60)
print("LangSmith Connection Test")
print("=" * 60)
print()

# Check environment variables
api_key = os.getenv("LANGSMITH_API_KEY")
project = os.getenv("LANGSMITH_PROJECT", "default")
tracing = os.getenv("LANGSMITH_TRACING_V2", "true")

print("1. Environment Variables:")
print(f"   LANGSMITH_API_KEY: {'[OK] Set' if api_key else '[ERROR] NOT SET'}")
if api_key:
    if api_key == "your_api_key_here":
        print("   [WARN] Still using placeholder value!")
    elif not (api_key.startswith("lsv2_pt_") or api_key.startswith("lsv2_sk_")):
        print(f"   [WARN] Key format looks wrong (should start with 'lsv2_pt_' or 'lsv2_sk_')")
        print(f"   Current: {api_key[:20]}...")
    else:
        key_type = "Project Token" if api_key.startswith("lsv2_pt_") else "Secret Key"
        print(f"   [OK] Format looks correct ({key_type}): {api_key[:15]}...")

print(f"   LANGSMITH_PROJECT: {project}")
print(f"   LANGSMITH_TRACING_V2: {tracing}")
print()

# Test imports
print("2. Testing LangSmith Import:")
try:
    from app.ai.langsmith_config import (
        is_langsmith_enabled,
        get_langsmith_client,
        LANGSMITH_PROJECT,
        LANGSMITH_API_KEY
    )
    print("   [OK] LangSmith module imported successfully")
    print(f"   Project from config: {LANGSMITH_PROJECT}")
    print(f"   API Key in config: {'[OK] Set' if LANGSMITH_API_KEY else '[ERROR] NOT SET'}")
except ImportError as e:
    print(f"   [ERROR] Failed to import: {e}")
    print("   -> Run: pip install langsmith")
    sys.exit(1)
except Exception as e:
    print(f"   [ERROR] Error: {e}")
    sys.exit(1)

print()

# Test initialization
print("3. Testing LangSmith Initialization:")
try:
    enabled = is_langsmith_enabled()
    print(f"   LangSmith Enabled: {'[OK] Yes' if enabled else '[ERROR] No'}")
    
    if enabled:
        client = get_langsmith_client()
        if client:
            print("   [OK] LangSmith client initialized")
            print(f"   [OK] Ready to send traces to project: '{LANGSMITH_PROJECT}'")
        else:
            print("   [ERROR] Failed to initialize client")
            print("   -> Check API key is valid")
    else:
        print("   [ERROR] LangSmith is disabled")
        print("   -> Set LANGSMITH_API_KEY environment variable")
        
except Exception as e:
    print(f"   [ERROR] Error during initialization: {e}")
    import traceback
    traceback.print_exc()

print()

# Test OpenAI wrapping
print("4. Testing OpenAI Client Wrapping:")
try:
    from app.ai.langsmith_config import wrap_openai_client
    from openai import OpenAI
    
    test_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "test"))
    wrapped = wrap_openai_client(test_client)
    
    if wrapped == test_client:
        if not is_langsmith_enabled():
            print("   [WARN] Client not wrapped (LangSmith disabled - this is OK)")
        else:
            print("   [WARN] Client not wrapped (check LangSmith initialization)")
    else:
        print("   [OK] OpenAI client wrapped with LangSmith")
        
except Exception as e:
    print(f"   [WARN] Could not test wrapping: {e}")

print()
print("=" * 60)
print("Summary:")
print("=" * 60)

if api_key and (api_key.startswith("lsv2_pt_") or api_key.startswith("lsv2_sk_")) and is_langsmith_enabled():
    print("[OK] Configuration looks good!")
    print()
    print("Next steps:")
    print("1. Make sure this matches your LangSmith dashboard project name:")
    print(f"   Project: '{project}'")
    print("2. Send a test message through your chatbot")
    print("3. Wait 10-30 seconds")
    print("4. Check LangSmith dashboard: https://smith.langchain.com")
    print(f"5. Look for project: '{project}'")
else:
    print("[ERROR] Configuration issues found:")
    if not api_key:
        print("   - LANGSMITH_API_KEY not set")
    elif not (api_key.startswith("lsv2_pt_") or api_key.startswith("lsv2_sk_")):
        print("   - LANGSMITH_API_KEY format incorrect (should start with 'lsv2_pt_' or 'lsv2_sk_')")
    if not is_langsmith_enabled():
        print("   - LangSmith not enabled")
    print()
    print("Fix the issues above and run this test again.")

print("=" * 60)

