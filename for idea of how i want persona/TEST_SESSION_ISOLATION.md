# Testing Session Isolation

## ✅ Migration Applied & Deployed

You've successfully:
- ✅ Run the migration in Supabase
- ✅ Deployed to Vercel

Now let's verify that session isolation is working correctly.

---

## 🧪 Test Plan

### Test 1: Basic Session Isolation

**Goal**: Verify that each chat session only sees its own messages.

**Steps**:
1. **Open Chat Session A** (create a new chat)
2. **Send message in Session A**: 
   ```
   "My favorite color is blue"
   ```
3. **Wait for response**
4. **Open Chat Session B** (create a NEW chat - different session)
5. **Send message in Session B**:
   ```
   "My favorite color is red"
   ```
6. **Wait for response**
7. **Go back to Session A** and ask:
   ```
   "What's my favorite color?"
   ```
8. **Expected Result**: Should say "blue" (from Session A only)
   - ✅ **PASS**: If it says "blue"
   - ❌ **FAIL**: If it says "red" or mentions both colors

---

### Test 2: RAG Context Isolation

**Goal**: Verify RAG only retrieves messages from current session.

**Steps**:
1. **Session A**: Send multiple messages
   ```
   "I'm working on a fitness coaching business"
   "My target audience is busy professionals"
   "I help them build sustainable habits"
   ```

2. **Session B**: Send different messages
   ```
   "I'm a software developer"
   "I build web applications"
   "I specialize in React and Python"
   ```

3. **In Session A**, ask:
   ```
   "What do I do for work?"
   ```
   - ✅ **PASS**: Should mention "fitness coaching" (from Session A)
   - ❌ **FAIL**: If it mentions "software developer" (from Session B)

4. **In Session B**, ask:
   ```
   "What do I do for work?"
   ```
   - ✅ **PASS**: Should mention "software developer" (from Session B)
   - ❌ **FAIL**: If it mentions "fitness coaching" (from Session A)

---

### Test 3: Document Context (Should Still Work)

**Goal**: Verify document retrieval still works (documents are NOT session-specific).

**Steps**:
1. **In any session**, ask:
   ```
   "Who are my potential clients?"
   ```
   - ✅ **PASS**: Should use document context (Avatar Sheet/ICP document)
   - ✅ **PASS**: Should provide detailed answer from documents

2. **In any session**, ask:
   ```
   "What's my tone?"
   ```
   - ✅ **PASS**: Should use document context (North Star/Brand Vision)
   - ✅ **PASS**: Should provide comprehensive answer from documents

**Note**: Document retrieval should work in ALL sessions (documents are shared, not session-specific).

---

### Test 4: Multiple Sessions Simultaneously

**Goal**: Verify multiple sessions can run without interference.

**Steps**:
1. **Open 3 different chat sessions** (A, B, C)
2. **Send different context in each**:
   - Session A: "I'm planning a vacation to Japan"
   - Session B: "I'm learning Spanish"
   - Session C: "I'm training for a marathon"
3. **Ask in each session**: "What am I working on?"
   - ✅ **PASS**: Each session gives correct answer for that session only
   - ❌ **FAIL**: If any session mentions content from another session

---

## 🔍 How to Check Backend Logs

### In Vercel Logs, look for:

**✅ Good Signs** (Session isolation working):
```
[RAG] Getting RAG context for query: '...'
SUCCESS: Found X similar user messages
```

**❌ Warning Signs** (Session isolation broken):
```
[SECURITY] WARNING: Found message from different session!
```

### Check RAG Retrieval:
```
[RAG] ✅ Context retrieved: X messages, Y document chunks, Z global patterns
```

If you see messages retrieved, they should only be from the current session.

---

## 🐛 Troubleshooting

### Issue: Sessions still overlapping

**Check**:
1. Verify migration ran successfully in Supabase:
   ```sql
   SELECT proname, pg_get_function_identity_arguments(oid) as args
   FROM pg_proc 
   WHERE proname = 'get_similar_user_messages';
   ```
   - Should show function with `query_session_id UUID` parameter

2. Check Vercel deployment logs for errors
3. Verify `session_id` is being passed in backend logs

### Issue: No messages retrieved in RAG

**Possible causes**:
- Messages haven't been embedded yet (wait a few seconds)
- Similarity threshold too high (should be 0.1)
- No messages in current session

**Check**:
```sql
-- In Supabase SQL Editor
SELECT COUNT(*) FROM message_embeddings WHERE session_id = 'YOUR_SESSION_ID';
```

### Issue: Documents not working

**This is separate from session isolation** - documents are shared across sessions.

**Check**:
- Documents are ingested (run test script)
- RAG retrieval is working (check logs)

---

## ✅ Success Criteria

Session isolation is working if:

1. ✅ Each chat session only sees its own messages
2. ✅ RAG context is session-specific
3. ✅ No cross-session message leakage
4. ✅ Document retrieval still works (shared across sessions)
5. ✅ Multiple sessions can run simultaneously without interference

---

## 📝 Quick Test Checklist

- [ ] Test 1: Basic session isolation (favorite color test)
- [ ] Test 2: RAG context isolation (work/profession test)
- [ ] Test 3: Document context still works
- [ ] Test 4: Multiple sessions simultaneously
- [ ] Check backend logs for warnings
- [ ] Verify no cross-session contamination

---

## 🎯 Expected Behavior

### ✅ CORRECT (Session Isolation Working):
```
Session A: "My name is John"
Session A: "What's my name?" → "John" ✅

Session B: "My name is Jane"  
Session B: "What's my name?" → "Jane" ✅
```

### ❌ INCORRECT (Session Isolation Broken):
```
Session A: "My name is John"
Session A: "What's my name?" → "John and Jane" ❌ (leaked from Session B)
```

---

**Ready to test?** Start with Test 1 (favorite color) - it's the simplest and will quickly show if isolation is working!


