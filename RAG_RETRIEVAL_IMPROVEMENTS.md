# RAG Retrieval Improvements - Fix Summary

## Issues Identified

1. **Wrong Documents Retrieved**: Query "what's my tone" was retrieving general "tone" content from video/retention documents instead of brand tone documents
2. **Too Few Chunks**: Only retrieving 2 chunks when we need more for comprehensive answers
3. **Generic Responses**: AI not using document context effectively
4. **Timeout**: 60-second timeout after response (background tasks)

## Fixes Applied

### 1. Improved Query Expansion for Tone Queries

**Before:**
```python
return f"{query} tone voice writing style brand identity north star brand vision"
```

**After:**
```python
return f"{query} Simon brand tone voice writing style brand identity north star brand vision Fit For Life Coaching brand philosophy messaging rules calm authority grounded intelligent emotionally honest"
```

**Why**: More specific keywords help match brand documents (Document 6 - Brand North Star, Document 2 - Purple Cow) instead of general content documents.

### 2. Increased Document Retrieval Count

**Before:** `match_count=10`

**After:** `match_count=15`

**Why**: More chunks = better coverage, especially for questions that might span multiple documents.

### 3. Enhanced System Prompt

**Added instructions:**
- "When asked about tone, voice, style → Reference the North Star / Brand Vision documents AND provide DETAILED, SPECIFIC answers"
- "If asked about tone/style/voice → Provide COMPREHENSIVE answers with specific examples, not generic descriptions"
- "ALWAYS quote or reference specific details from the document context when answering"

**Why**: Forces AI to use document context more effectively and provide detailed answers.

## Expected Improvements

### Before:
- Query: "what's my tone"
- Retrieved: 2 chunks about general video tone
- Response: Generic "emotionally real, direct, human" (174 chars)

### After:
- Query: "what's my tone" 
- Retrieved: 15 chunks (including brand documents)
- Response: Detailed answer with specific brand guidelines, examples, and document references

## Testing

After deployment, test with:
1. "What's my tone?" - Should retrieve brand documents and give detailed answer
2. "Tell me about yourself" - Should use personal description document
3. "How should I use the Avatar Sheet?" - Should use document explanation guide

## Timeout Issue

The 60-second timeout is happening because background tasks (embedding storage, session updates) are still running after the stream completes. These are already non-blocking (`asyncio.create_task()`), but Vercel might be waiting for them.

**Current Status**: Background tasks have timeouts (2-3 seconds each), but if multiple tasks run sequentially, they could exceed 60 seconds total.

**Next Steps**: 
- Monitor if timeout persists after retrieval improvements
- If it does, we may need to make background tasks even more fire-and-forget

## Files Changed

1. `app/ai/rag_service.py`:
   - Improved query expansion for tone queries
   - Increased match_count from 10 to 15

2. `app/ai/models.py`:
   - Enhanced system prompt to better use document context
   - Added instructions for detailed, specific answers

## Deployment

These changes need to be deployed to take effect:
- Query expansion improvements
- Increased retrieval count
- Enhanced system prompt

The documents are already in the database (no deployment needed for that).

