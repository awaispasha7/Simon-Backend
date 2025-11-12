# Web Search Integration with RAG

## ✅ Current Flow: RAG First, Then Web Search

Yes, your understanding is **CORRECT**! Here's exactly how it works:

### Step-by-Step Flow:

1. **User enters a prompt** → Received by `/api/v1/chat` endpoint

2. **RAG Context Retrieval (FIRST)** → Happens BEFORE web search:
   - Query expansion (`_expand_brand_query`) adds relevant keywords
   - Embedding generation for the query
   - **Document retrieval** from Supabase (15 chunks from brand documents)
   - **User message retrieval** from Supabase (6 similar previous messages)
   - **Global knowledge retrieval** from Supabase (3 patterns)
   - All RAG context is formatted and added to the system prompt

3. **System Prompt Construction**:
   - Base system prompt (Simon's Personal Content Strategist)
   - **RAG context is inserted** (documents, user messages, global knowledge)
   - Instructions to use RAG context for brand questions

4. **Web Search Tool Setup**:
   - If `enable_web_search` is True (or not explicitly False), web search tool is made available
   - Tool definition: `internet_search` function
   - AI can decide to use it OR it's forced if explicit triggers detected

5. **AI Processing**:
   - AI receives: User prompt + RAG context + Web search tool (if enabled)
   - AI decides: Should I search the web? (or is forced to search)
   - If AI calls `internet_search`:
     - Web search is performed (Tavily API)
     - Results are formatted and added to conversation
     - AI generates response using **BOTH RAG context AND web search results**

6. **Final Response**:
   - Combines information from:
     - ✅ **RAG context** (brand documents, previous conversations)
     - ✅ **Web search results** (current information from internet)
   - AI synthesizes both sources into a comprehensive answer

## 📊 Code Flow:

```python
# In simple_chat.py
1. Get RAG context FIRST
   rag_context = await rag_service.get_rag_context(...)
   
2. Generate AI response with RAG + Web search option
   ai_response = await ai_manager.generate_response(
       rag_context=rag_context,  # RAG context included
       web_search_enabled=True   # Web search tool available
   )

# In models.py (_generate_chat_response)
1. Add RAG context to system prompt
   if rag_context:
       rag_context_text = rag_context.get('combined_context_text')
       # RAG context is inserted into system prompt

2. Setup web search tool
   web_search_function = self._get_web_search_function()
   tools = [web_search_function] if web_search_function else None

3. AI processes with both:
   - System prompt (includes RAG context)
   - User message
   - Web search tool (if enabled)

4. If AI calls web search:
   - Search is performed
   - Results added to messages
   - AI generates final response using BOTH sources
```

## 🎯 When Web Search is Used:

### Automatic Triggers (AI decides):
- User asks about current events, recent news
- User asks about latest information, statistics, data
- User asks "what's the latest" or "current" information
- User asks about recent research or studies

### Explicit Triggers (Forced search):
- User says "search for", "look up", "find information about"
- User says "search:", "internet search"
- User explicitly requests search

### When Web Search is NOT Used:
- User asks about brand documents (RAG handles this)
- User asks "What's my tone?" (RAG handles this)
- User asks "Who are my clients?" (RAG handles this)
- User creates scripts/content (RAG handles this)
- Web search is explicitly disabled (`enable_web_search: false`)

## 🔄 Ideal Flow (Current Implementation):

```
User Query
    ↓
RAG Retrieval (FIRST)
    ├─ Document chunks (15)
    ├─ User messages (6)
    └─ Global knowledge (3)
    ↓
RAG Context Added to System Prompt
    ↓
Web Search Tool Available (if enabled)
    ↓
AI Processes Query
    ├─ Has RAG context ✅
    └─ Can use web search if needed ✅
    ↓
If AI calls web search:
    ├─ Search performed
    ├─ Results added to conversation
    └─ AI generates response using BOTH
    ↓
Final Response
    ├─ Uses RAG context (brand documents)
    └─ Uses web search results (current info)
```

## ✅ This is the CORRECT Flow!

**Why RAG First?**
- Brand documents are the PRIMARY source of truth
- RAG context should ALWAYS be available for brand questions
- Web search is supplementary for current/recent information

**Why Combine Both?**
- RAG provides: Brand identity, tone, rules, guidelines (from documents)
- Web search provides: Current events, latest trends, recent research
- Together: Comprehensive answers that are both brand-aligned AND current

## 📝 Example:

**User Query**: "What are the latest fitness trends in 2025?"

1. **RAG Retrieval**:
   - Retrieves brand documents about content strategy
   - Retrieves previous conversations about fitness topics
   - Adds context about Simon's brand approach to trends

2. **Web Search**:
   - AI decides to search: "latest fitness trends 2025"
   - Gets current information from web
   - Results added to conversation

3. **Final Response**:
   - Uses RAG context: "Based on your brand approach, you focus on..."
   - Uses web search: "Current trends show..."
   - Combines both: Brand-aligned answer with current information

## 🔧 Configuration:

**Enable Web Search:**
- Set `TAVILY_API_KEY` in environment variables
- Frontend can toggle via `enable_web_search` flag
- Default: Enabled if API key is set

**Disable Web Search:**
- Set `enable_web_search: false` in chat request
- Or don't set `TAVILY_API_KEY`

## 🎯 Summary:

✅ **RAG happens FIRST** - Retrieves relevant context from embeddings
✅ **Web search is COMBINED** - Adds current information when needed
✅ **Both are used together** - AI synthesizes RAG context + web results
✅ **This is the ideal flow** - Brand documents are primary, web search is supplementary

The current implementation is **CORRECT** and follows best practices! 🎉


