# Troubleshooting: No Traces in LangSmith Dashboard

## 🔍 Step-by-Step Diagnosis

### Step 1: Check if LangSmith is Initialized

**In your backend logs (Vercel or local), look for:**

✅ **Success messages:**
```
[OK] LangSmith monitoring enabled (project: default)
[OK] LangSmith client initialized
[OK] OpenAI client wrapped with LangSmith tracing
```

❌ **Warning messages:**
```
[WARN] LangSmith monitoring disabled (set LANGSMITH_API_KEY to enable)
```

**If you see warnings:**
- LangSmith API key is not set or incorrect
- Go to Step 2

**If you see success messages but no traces:**
- Go to Step 3

---

### Step 2: Verify Environment Variables

#### For Local Development:

1. **Check your `.env` file exists:**
   ```bash
   # In Simon-Backend directory
   ls .env
   ```

2. **Verify the API key format:**
   ```env
   LANGSMITH_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   - Should start with `lsv2_pt_` (project token) or `lsv2_sk_` (org-scoped secret key)
   - Should be your actual key (not "your_api_key_here")
   - **If your key starts with `lsv2_sk_`**, you MUST also set `LANGSMITH_WORKSPACE_ID`

3. **Check project name:**
   ```env
   LANGSMITH_PROJECT=default
   ```

4. **If using org-scoped key (lsv2_sk_*), add workspace ID:**
   ```env
   LANGSMITH_WORKSPACE_ID=your_workspace_id
   ```
   - Find it in LangSmith dashboard → Settings → Workspace
   - Required for org-scoped API keys
   - Should match the project name in LangSmith dashboard

#### For Production (Vercel):

1. **Go to Vercel Dashboard:**
   - Your Project → Settings → Environment Variables

2. **Verify these variables exist:**
   - `LANGSMITH_API_KEY` = `lsv2_pt_...` or `lsv2_sk_...` (your real key)
   - `LANGSMITH_PROJECT` = `default`
   - `LANGSMITH_WORKSPACE_ID` = `your_workspace_id` (required if API key is `lsv2_sk_*`)
   - `LANGSMITH_TRACING_V2` = `true`

3. **Check environment scope:**
   - Make sure variables are set for **Production** (or All)
   - Preview/Development might have different values

4. **Redeploy after adding variables:**
   - Vercel → Deployments → Click "..." → Redeploy

---

### Step 3: Test if Traces are Being Sent

#### Option A: Check Vercel Logs

1. Go to Vercel Dashboard
2. Your Project → Logs
3. Send a test message through your chatbot
4. Look for:
   - `[OK] LangSmith monitoring enabled`
   - Any LangSmith-related messages
   - Errors mentioning LangSmith

#### Option B: Add Debug Logging

Temporarily add this to see if traces are created:

```python
# In app/ai/langsmith_config.py, add after line 167:
if is_langsmith_enabled():
    print(f"[DEBUG] LangSmith API Key: {LANGSMITH_API_KEY[:10]}...")  # First 10 chars
    print(f"[DEBUG] LangSmith Project: {LANGSMITH_PROJECT}")
    print(f"[DEBUG] LangSmith Client: {get_langsmith_client()}")
```

---

### Step 4: Verify Project Name Match

**Critical:** The project name in your code must match LangSmith dashboard!

1. **Check your `.env` or Vercel:**
   ```
   LANGSMITH_PROJECT=default
   ```

2. **Check LangSmith dashboard:**
   - URL shows: `.../default` or `.../simon-chatbot`
   - Top navigation shows project name

3. **If they don't match:**
   - Either change `.env` to match dashboard
   - Or create a new project in LangSmith with matching name

---

### Step 5: Test with a Simple Request

1. **Send a test message through your chatbot:**
   - Any simple message like "hello" or "test"

2. **Wait 5-10 seconds** (traces may take a moment to appear)

3. **Refresh LangSmith dashboard**

4. **Check:**
   - "Runs" tab should show new entries
   - Look for names like:
     - `generate_chat_response`
     - `get_rag_context`
     - `generate_embedding`

---

### Step 6: Check for Errors

1. **In LangSmith dashboard:**
   - Filter: `has_error:true`
   - See if traces are being created but failing

2. **In Vercel logs:**
   - Look for LangSmith-related errors
   - Check for import errors
   - Check for API key authentication errors

---

## 🐛 Common Issues & Solutions

### Issue 1: "LangSmith monitoring disabled"

**Cause:** API key not set

**Solution:**
- Add `LANGSMITH_API_KEY` to `.env` (local) or Vercel (production)
- Restart server / Redeploy

---

### Issue 2: "Failed to initialize LangSmith client"

**Cause:** Invalid API key or network issue

**Solution:**
- Verify API key is correct (starts with `lsv2_pt_`)
- Check API key hasn't expired
- Verify network connectivity

---

### Issue 3: Traces appear in different project

**Cause:** Project name mismatch

**Solution:**
- Check `LANGSMITH_PROJECT` matches dashboard project name
- Or switch to correct project in LangSmith dashboard

---

### Issue 4: Traces delayed or not appearing

**Cause:** LangSmith may batch traces

**Solution:**
- Wait 10-30 seconds after sending message
- Refresh dashboard
- Check "Last 7 days" filter isn't hiding recent traces

---

### Issue 5: Only some traces appear

**Cause:** Some operations might not be traced

**Solution:**
- Check which operations have tracing:
  - ✅ Chat responses (wrapped OpenAI client)
  - ✅ Embeddings (wrapped AsyncOpenAI client)
  - ✅ RAG operations (manual tracing)
  - ✅ Document processing (manual tracing)

---

## ✅ Quick Verification Checklist

- [ ] `LANGSMITH_API_KEY` is set (not "your_api_key_here")
- [ ] API key starts with `lsv2_pt_` or `lsv2_sk_`
- [ ] If API key starts with `lsv2_sk_`, `LANGSMITH_WORKSPACE_ID` is set
- [ ] `LANGSMITH_PROJECT` matches dashboard project name
- [ ] Server logs show `[OK] LangSmith monitoring enabled`
- [ ] Vercel environment variables are set (if production)
- [ ] Vercel redeployed after adding variables
- [ ] Sent a test message through chatbot
- [ ] Waited 10-30 seconds
- [ ] Refreshed LangSmith dashboard
- [ ] Checked correct project in dashboard
- [ ] Filter set to "Last 7 days" or "All time"

---

## 🔧 Quick Fix Script

Run this to verify your setup:

```python
# test_langsmith_setup.py
import os
from dotenv import load_dotenv

load_dotenv()

print("=== LangSmith Configuration Check ===")
print()

api_key = os.getenv("LANGSMITH_API_KEY")
project = os.getenv("LANGSMITH_PROJECT", "default")
tracing = os.getenv("LANGSMITH_TRACING_V2", "true")

print(f"LANGSMITH_API_KEY: {'✅ Set' if api_key else '❌ NOT SET'}")
if api_key:
    print(f"  Format: {api_key[:10]}... (should start with 'lsv2_pt_')")
    print(f"  Valid: {'✅' if api_key.startswith('lsv2_pt_') else '❌ Invalid format'}")

print(f"LANGSMITH_PROJECT: {project}")
print(f"LANGSMITH_TRACING_V2: {tracing}")

print()
print("=== Testing LangSmith Import ===")
try:
    from app.ai.langsmith_config import is_langsmith_enabled, get_langsmith_client
    enabled = is_langsmith_enabled()
    print(f"LangSmith Enabled: {'✅ Yes' if enabled else '❌ No'}")
    
    if enabled:
        client = get_langsmith_client()
        print(f"LangSmith Client: {'✅ Initialized' if client else '❌ Failed to initialize'}")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=== Next Steps ===")
if not api_key:
    print("1. Add LANGSMITH_API_KEY to .env file")
if api_key and not api_key.startswith('lsv2_pt_'):
    print("1. Verify API key format (should start with 'lsv2_pt_')")
if api_key and api_key.startswith('lsv2_pt_'):
    print("1. ✅ API key looks valid")
    print("2. Restart your server")
    print("3. Send a test message")
    print("4. Check LangSmith dashboard in 10-30 seconds")
```

---

## 📞 Still Not Working?

If traces still don't appear after checking all above:

1. **Check Vercel Function Logs:**
   - Vercel → Your Project → Logs
   - Look for any errors during request handling

2. **Verify Code is Deployed:**
   - Check latest deployment in Vercel
   - Ensure LangSmith integration code is in deployed version

3. **Test Locally First:**
   - Run locally with `.env` file
   - Verify traces appear in local testing
   - Then deploy to production

4. **Check LangSmith Account:**
   - Verify account is active
   - Check if there are any usage limits
   - Verify API key hasn't been revoked

