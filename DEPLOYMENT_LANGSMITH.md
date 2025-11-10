# LangSmith Deployment Guide

## ✅ Pre-Push Checklist

### 1. Verify .env is NOT being committed
```bash
# Check if .env is tracked (should return nothing)
git ls-files | grep .env

# If .env shows up, remove it:
git rm --cached .env
```

### 2. Your .env file should contain (LOCALLY ONLY):
```env
LANGSMITH_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Your REAL key
LANGSMITH_PROJECT=default
LANGSMITH_WORKSPACE_ID=your_workspace_id  # Required if API key is org-scoped (lsv2_sk_)
LANGSMITH_TRACING_V2=true
```

**Important:** If your API key starts with `lsv2_sk_` (org-scoped), you MUST also set `LANGSMITH_WORKSPACE_ID`.
Find your workspace ID in LangSmith dashboard → Settings → Workspace.

**⚠️ DO NOT commit this file!** It's already in `.gitignore`.

---

## 🚀 Production Deployment (Vercel)

### Step 1: Push Your Code
```bash
git add .
git commit -m "Add LangSmith monitoring integration"
git push origin main
```

### Step 2: Add Environment Variables in Vercel

1. Go to your Vercel project dashboard
2. Navigate to: **Settings → Environment Variables**
3. Add these variables:

#### For Production:
```
LANGSMITH_API_KEY = lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGSMITH_PROJECT = default
LANGSMITH_WORKSPACE_ID = your_workspace_id  # Required if API key is org-scoped (lsv2_sk_)
LANGSMITH_TRACING_V2 = true
```

#### For Preview/Development (optional):
- Same variables as above
- Or use different project names like `simon-chatbot-dev`

### Step 3: Redeploy

After adding environment variables:
- Vercel will automatically redeploy
- Or manually trigger: **Deployments → Redeploy**

---

## ✅ Verification

### After Deployment:

1. **Check Vercel Logs:**
   - Look for: `[OK] LangSmith monitoring enabled`
   - Should NOT see: `[WARN] LangSmith monitoring disabled`

2. **Test Your Chatbot:**
   - Send a test message
   - Check LangSmith dashboard: https://smith.langchain.com
   - You should see traces appearing in the "default" project

3. **Verify Traces:**
   - Look for traces named:
     - `generate_chat_response`
     - `get_rag_context`
     - `generate_embedding`
     - `process_document`

---

## 🔒 Security Notes

- ✅ `.env` files are in `.gitignore` - safe to push
- ✅ Never commit API keys to git
- ✅ Use Vercel's environment variables for production
- ✅ Different keys for dev/staging/production (recommended)

---

## 📝 Quick Reference

### Local Development:
- Uses `.env` file in `Simon-Backend/` directory
- Automatically loaded by `python-dotenv`

### Production (Vercel):
- Set in Vercel dashboard: Settings → Environment Variables
- Available to all serverless functions
- Automatically loaded by Python's `os.getenv()`

---

## 🆘 Troubleshooting

### No traces appearing in LangSmith?
1. Check Vercel logs for LangSmith initialization
2. Verify `LANGSMITH_API_KEY` is set correctly in Vercel
3. Check API key is valid (starts with `lsv2_pt_`)
4. Ensure project name matches: `LANGSMITH_PROJECT=default`

### Getting "LangSmith monitoring disabled"?
- API key not set in environment variables
- Check Vercel environment variables are saved
- Redeploy after adding variables

