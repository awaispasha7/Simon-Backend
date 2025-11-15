# How to Trigger Web Search

## 🎯 3 Ways to Trigger Web Search

### 1. **Frontend Toggle (Globe Icon)** ✅ EASIEST METHOD

**Location**: In the chat input box, there's a **Globe icon** (🌐) button

**How to Use**:
1. Click the **Globe icon** in the chat composer (next to the send button)
2. When enabled, the icon turns **blue** (active state)
3. When disabled, the icon is **gray** (inactive state)
4. Send your message - web search will be enabled for that query

**Visual Indicator**:
- 🔵 **Blue Globe** = Web search **ENABLED**
- ⚪ **Gray Globe** = Web search **DISABLED**

**Code Location**: `Simon-Chatbot-Frontend/src/components/Composer.tsx`
```typescript
const [enableWebSearch, setEnableWebSearch] = useState(false)

// Globe icon button
<button onClick={() => setEnableWebSearch(!enableWebSearch)}>
  <Globe style={{ color: enableWebSearch ? 'blue' : 'gray' }} />
</button>
```

---

### 2. **Explicit Keywords in Query** 🔍 AUTOMATIC TRIGGER

**How it Works**: If your query contains specific keywords, web search is **automatically forced** (even if globe icon is off)

**Keywords that Force Search**:
- "search for"
- "look up"
- "find information about"
- "what's the latest"
- "current news"
- "recent research"
- "latest statistics"
- "current data"
- "recent study"
- "latest trends"
- "what happened"
- "news about"
- "search:"
- "google:"
- "internet search"

**Examples**:
```
✅ "Search for latest fitness trends"
✅ "Look up recent research on nutrition"
✅ "What's the latest news about fitness?"
✅ "Find information about current statistics"
✅ "search: fitness trends 2025"
```

**Code Location**: `Simon-Chatbot-Backend/app/ai/models.py`
```python
def _should_force_search(self, prompt: str) -> bool:
    search_keywords = [
        "search for", "look up", "find information about",
        "what's the latest", "current news", "recent research",
        # ... more keywords
    ]
    return any(keyword in prompt_lower for keyword in search_keywords)
```

---

### 3. **AI Automatic Decision** 🤖 SMART TRIGGER

**How it Works**: The AI automatically decides to search when:
- Query asks about **current events** or **recent news**
- Query asks about **latest information** or **statistics**
- Query asks "what's the latest" or "current" information
- Query asks about **recent research** or **studies**
- Information might not be in training data (pre-2024)

**Examples**:
```
✅ "What are the latest fitness trends?" → AI decides to search
✅ "Current statistics on obesity" → AI decides to search
✅ "Recent research on intermittent fasting" → AI decides to search
✅ "What happened in fitness industry this year?" → AI decides to search
```

**When AI WON'T Search**:
- Brand questions: "What's my tone?" → Uses RAG (documents)
- Content creation: "Create a script" → Uses RAG (documents)
- Personal questions: "Who are my clients?" → Uses RAG (documents)

**Code Location**: `Simon-Chatbot-Backend/app/ai/models.py`
```python
# Web search function description tells AI when to use it
"description": "Search the internet for current information, facts, news, or data that may not be in the training data. ALWAYS use this when: 1) User explicitly asks to search, 2) User asks about current events, recent news, or latest information, 3) User asks about statistics, data, or facts that may have changed..."
```

---

## 📊 Priority Order

When multiple triggers are present, priority is:

1. **Explicit Keywords** (Highest Priority)
   - Forces search even if globe icon is OFF
   - Example: "search for fitness trends" → **FORCED SEARCH**

2. **Globe Icon Toggle**
   - If enabled, makes search tool available
   - AI can still decide whether to use it
   - Example: Globe ON + "What are fitness trends?" → **AI DECIDES**

3. **AI Automatic Decision**
   - Only works if globe icon is ON or explicit keywords present
   - AI analyzes query and decides if search is needed
   - Example: Globe ON + "Latest fitness research" → **AI DECIDES TO SEARCH**

---

## 🔧 Backend Configuration

### Enable Web Search Service

**Required**: Set `TAVILY_API_KEY` in environment variables

```bash
# In .env file or Vercel environment variables
TAVILY_API_KEY=your_tavily_api_key_here
```

**Check if Enabled**:
```python
# In web_search.py
if api_key and api_key != "your_tavily_api_key_here":
    self.enabled = True
```

### Disable Web Search

**Method 1**: Don't set `TAVILY_API_KEY` → Web search disabled globally

**Method 2**: Frontend sends `enable_web_search: false` → Disabled for that query

**Method 3**: Backend checks `enable_web_search` flag:
```python
if enable_web_search is False:
    tools = None  # Web search disabled
    print("Web search disabled by user")
```

---

## 🎯 Complete Flow Example

### Example 1: User Clicks Globe Icon

```
1. User clicks Globe icon → enableWebSearch = true
2. User types: "What are fitness trends?"
3. Frontend sends: { text: "What are fitness trends?", enable_web_search: true }
4. Backend: Web search tool available
5. AI: Decides to search (query about trends)
6. Web search: Searches "latest fitness trends 2025"
7. Response: Combines RAG context + Web search results
```

### Example 2: Explicit Keyword

```
1. Globe icon: OFF (enableWebSearch = false)
2. User types: "Search for latest fitness trends"
3. Frontend sends: { text: "Search for latest fitness trends", enable_web_search: false }
4. Backend: Detects "search for" → FORCES search
5. Web search: Searches "latest fitness trends 2025"
6. Response: Uses web search results
```

### Example 3: AI Automatic Decision

```
1. Globe icon: ON (enableWebSearch = true)
2. User types: "What's the latest research on nutrition?"
3. Frontend sends: { text: "...", enable_web_search: true }
4. Backend: Web search tool available
5. AI: Analyzes query → Decides to search (asks about "latest research")
6. Web search: Searches "latest research nutrition 2025"
7. Response: Combines RAG + Web search
```

---

## 🚨 Troubleshooting

### Web Search Not Working?

1. **Check TAVILY_API_KEY**:
   ```bash
   # In backend logs, look for:
   [WebSearch] ✅ Tavily client initialized  # ✅ Working
   [WebSearch] ⚠️ TAVILY_API_KEY not set     # ❌ Not configured
   ```

2. **Check Globe Icon**:
   - Is it blue? → Enabled
   - Is it gray? → Disabled (click to enable)

3. **Check Query**:
   - Does it have explicit keywords? → Should force search
   - Is it about current/recent info? → AI should decide to search

4. **Check Backend Logs**:
   ```
   🔍 [WebSearch] Web search tool enabled - AI can search the internet when needed
   🔍 [WebSearch] Function call requested: internet_search
   🔍 [WebSearch] Searching for: [query]
   🔍 [WebSearch] Found X results
   ```

---

## 📝 Summary

| Method | How to Trigger | Priority |
|--------|---------------|----------|
| **Globe Icon** | Click globe icon in chat input | Medium |
| **Explicit Keywords** | Use phrases like "search for", "look up" | **Highest** |
| **AI Decision** | Ask about current/recent information | Low (needs globe ON) |

**Best Practice**: 
- For guaranteed search → Use explicit keywords ("search for...")
- For convenience → Click globe icon and let AI decide
- For brand questions → Keep globe OFF (uses RAG only)

---

## 🎉 Quick Reference

**Enable Web Search**:
- ✅ Click Globe icon (turns blue)
- ✅ Use explicit keywords ("search for...")
- ✅ Ask about current/recent information

**Disable Web Search**:
- ❌ Click Globe icon again (turns gray)
- ❌ Don't use explicit keywords
- ❌ Ask brand questions (uses RAG instead)

**Force Web Search**:
- 🔍 Use explicit keywords (works even if globe is OFF)


