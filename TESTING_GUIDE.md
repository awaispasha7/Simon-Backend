# RAG Testing Guide - Client Requirements

## Pre-Testing Checklist

### 1. Verify Documents Are Ingested

**Check via API:**
```bash
# Get ingestion status
GET https://your-backend-url/api/v1/ingest/status

# Expected response should show:
# - embeddings_count > 0 (should be ~20 PDFs worth)
# - assets_count > 0
# - embeddings_by_user should show user_id: "00000000-0000-0000-0000-000000000001"
```

**Check via Supabase Dashboard:**
- Go to `document_embeddings` table
- Filter by `user_id = '00000000-0000-0000-0000-000000000001'`
- Should see hundreds/thousands of rows (chunks from ~20 PDFs)

### 2. Check Vercel Logs Are Accessible
- Go to Vercel Dashboard → Your Backend Project → Logs
- Look for `[RAG]` prefixed messages

---

## Test Cases (Based on Client Requirements)

### ✅ Test 1: Document Recognition - "Who is my niche?"

**Query:** `Who is my niche?`

**Expected Behavior:**
- ✅ RAG should retrieve ICP/target audience documents
- ✅ Response should reference specific information from uploaded documents
- ✅ Should NOT say "I don't have access to your documents"

**What to Check in Logs:**
```
[RAG] Getting RAG context for query: 'Who is my niche?...'
[RAG] ✅ Context retrieved: X messages, Y document chunks, Z global patterns
[RAG] ✅ Found Y document chunks - AI will use this!
[RAG]   Chunk 1: [ICP/PDF] (relevance: X.XX) [preview of chunk text]
```

**Success Criteria:**
- Response mentions specific niche/audience details from documents
- Response is specific, not generic
- Logs show document chunks were retrieved

---

### ✅ Test 2: Brand Tone & Voice Recognition

**Query:** `What's my tone?` or `How should I write?`

**Expected Behavior:**
- ✅ Retrieves brand guidelines documents
- ✅ References specific tone guidelines (emotional, real, conversational)
- ✅ Mentions sentence rhythm, emotional pacing, storytelling structure

**Success Criteria:**
- Response includes specific tone characteristics from documents
- References emotional, real, conversational style
- Mentions pacing/structure if in documents

---

### ✅ Test 3: Hook Formula Application

**Query:** `Create a hook for a video about [topic]`

**Expected Behavior:**
- ✅ Retrieves hook formula documents
- ✅ Applies hook formulas from documents
- ✅ Generates 2-3 hook options
- ✅ Uses brand tone and style

**Success Criteria:**
- Hooks follow formulas from documents
- Multiple options provided
- Matches brand tone

---

### ✅ Test 4: Script Creation with Full Structure

**Query:** `Create a 30-second video script about [topic]`

**Expected Behavior:**
- ✅ Includes Hook (emotionally powerful, scroll-stopping)
- ✅ Includes Story/Insight (emotional connection)
- ✅ Includes CTA (strong, specific, emotional)
- ✅ Provides 2-3 Hook options
- ✅ Provides 2-3 CTA options
- ✅ Includes caption suggestion
- ✅ Includes hashtags
- ✅ Includes thumbnail text ideas (4-6 words)
- ✅ Includes B-roll recommendations
- ✅ Includes background sound suggestions
- ✅ Applies brand rules automatically

**Success Criteria:**
- All required elements present
- Follows brand guidelines from documents
- No repetition, always relevant and emotionally strong

---

### ✅ Test 5: Weekly Content Strategy

**Query:** `Give me 5 ideas for this week`

**Expected Behavior:**
- ✅ Ideas relevant to brand, topics, audience pain points
- ✅ Categorized by content angle (emotional, educational, motivational, myth-busting)
- ✅ Each idea includes:
  - Hook idea
  - Main message
  - CTA direction
  - Recommended format (based on 4 core formats)

**Success Criteria:**
- 5 distinct ideas
- Categorized appropriately
- All required elements per idea
- Relevant to brand documents

---

### ✅ Test 6: Competitor Analysis & Adaptation

**Query:** `[Paste competitor transcript] - Rewrite this in my voice`

**Expected Behavior:**
- ✅ Analyzes competitor content
- ✅ Extracts key data and emotional triggers
- ✅ Rewrites in brand voice, tone, storytelling style
- ✅ Applies content rules, pacing, brand philosophy

**Success Criteria:**
- Rewritten content matches brand tone
- Key elements extracted and adapted
- Follows brand storytelling structure

---

### ✅ Test 7: Natural Editing Commands

**Query:** `Make it sound more human` or `Rewrite it in a more emotional tone` or `Simplify this for Instagram`

**Expected Behavior:**
- ✅ Understands contextual editing commands
- ✅ Executes edits smoothly
- ✅ Maintains brand consistency

**Success Criteria:**
- Edits are applied correctly
- Brand voice maintained
- Natural, conversational result

---

### ✅ Test 8: General Knowledge Query

**Query:** `How to lose fat`

**Expected Behavior:**
- ✅ Responds intelligently (like ChatGPT)
- ✅ Aligned with brand's approach (if applicable)
- ✅ Uses general knowledge + brand context if relevant

**Success Criteria:**
- Meaningful, helpful response
- Not generic "I can't help with that"
- Brand-aligned if topic relates to brand

---

### ✅ Test 9: Carousel Functionality

**Query:** `[Upload 5 competitor carousel screenshots] - Extract the data and build a carousel for my coaching`

**Expected Behavior:**
- ✅ Extracts text and visual structure from images
- ✅ Applies carousel rules from documents
- ✅ Suggests headline + slide structure options
- ✅ Outputs carousel text aligned with brand tone

**Success Criteria:**
- Data extracted from images
- Carousel rules applied
- Brand-aligned output

---

## How to Check Logs During Testing

### In Vercel Dashboard:
1. Go to your backend project
2. Click "Logs" tab
3. Filter by `[RAG]` or search for "RAG"

### Key Log Messages to Look For:

**✅ Good Signs:**
```
[RAG] Getting RAG context for query: '...'
[RAG] ✅ Context retrieved: X messages, Y document chunks, Z global patterns
[RAG] ✅ Found Y document chunks - AI will use this!
[RAG]   Chunk 1: [PDF] (relevance: 0.XX) [chunk preview]
📚 Including RAG context: X user messages, Y document chunks, Z global patterns
✅ RAG has Y document chunks - AI MUST use this context for brand questions!
```

**⚠️ Warning Signs:**
```
[RAG] ⚠️ No document chunks found - check if documents are properly ingested
[RAG] ⚠️ Timeout after 3s - continuing without RAG context
[RAG] ❌ Error - skipping RAG: [error message]
```

**🔴 Critical Issues:**
```
[RAG] ⚠️ RAG service not available
```

---

## Troubleshooting

### Issue: "No document chunks found"

**Possible Causes:**
1. Documents not ingested properly
2. Wrong user_id in RAG query
3. Documents ingested with different user_id

**Fix:**
1. Check `document_embeddings` table in Supabase
2. Verify `user_id = '00000000-0000-0000-0000-000000000001'`
3. Re-ingest documents if needed

### Issue: "RAG timeout"

**Possible Causes:**
1. Supabase RPC function slow
2. Too many documents to search
3. Network latency

**Fix:**
- Check Supabase performance
- Verify vector index is created
- Check network connection

### Issue: "AI not using document context"

**Possible Causes:**
1. RAG context not being passed to AI
2. AI instructions not strong enough
3. Document chunks not relevant to query

**Fix:**
- Check logs for `[RAG] ✅ Found X document chunks`
- Verify `rag_context_text` is in AI prompt
- Check if document chunks are actually relevant

---

## Success Metrics

After testing, you should see:

1. ✅ **Document Recognition:** Bot answers "Who is my niche?" with specific details
2. ✅ **Brand Consistency:** All responses follow brand tone and rules
3. ✅ **Script Quality:** Scripts include all required elements (Hook, Story, CTA, etc.)
4. ✅ **No Generic Responses:** Bot never says "I don't have access to your documents"
5. ✅ **RAG Working:** Logs show document chunks being retrieved for relevant queries
6. ✅ **Natural Interaction:** Editing commands work smoothly
7. ✅ **Content Strategy:** Weekly ideas are relevant and categorized

---

## Next Steps After Testing

1. **If RAG not working:**
   - Check document ingestion status
   - Verify user_id matches
   - Check Supabase RPC function exists

2. **If AI not using context:**
   - Check logs for document chunk retrieval
   - Verify AI prompt includes RAG context
   - Test with more specific queries

3. **If responses still generic:**
   - Verify documents contain relevant information
   - Check if similarity threshold is too high
   - Increase document chunk retrieval count

