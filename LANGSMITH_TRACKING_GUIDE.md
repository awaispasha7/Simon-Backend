# LangSmith Output Tracking Guide

## 🎯 Quick Start

1. **Access Dashboard:** https://smith.langchain.com
2. **Select Project:** Click on your project (default: "default" or "simon-chatbot")
3. **View Traces:** Go to "Runs" tab
4. **Click a Trace:** See full input/output details

---

## 📊 Understanding Your Traces

### Trace Types You'll See

#### 1. **Chat Responses** (`generate_chat_response`)
- **Type:** `llm`
- **Tags:** `chat`, `openai`, `llm`
- **What it shows:**
  - Full prompt sent to OpenAI (including RAG context)
  - Complete AI response
  - Model used (gpt-4o, gpt-4o-mini)
  - Token usage (input + output)
  - Latency
  - Metadata: RAG context counts, image count, etc.

#### 2. **Embeddings** (`generate_embedding`, `generate_query_embedding`)
- **Type:** `embedding`
- **Tags:** `embedding`, `openai`
- **What it shows:**
  - Text that was embedded
  - Embedding dimensions
  - Model used
  - Latency

#### 3. **RAG Context** (`get_rag_context`)
- **Type:** `chain`
- **Tags:** `rag`, `retrieval`, `context_building`
- **What it shows:**
  - User query
  - Retrieved document chunks count
  - Retrieved user messages count
  - Retrieved global knowledge count
  - Combined context text (what was sent to LLM)
  - Metadata: user_id, project_id, etc.

#### 4. **Document Processing** (`process_document`)
- **Type:** `chain`
- **Tags:** `document_processing`, `embedding`, `storage`
- **What it shows:**
  - Filename processed
  - Chunks created
  - Embeddings generated
  - Processing time
  - Success/failure status

---

## 🔍 How to Track Outputs

### Method 1: View All Traces (Runs Tab)

1. Go to **"Runs"** tab in LangSmith
2. You'll see a table with columns:
   - **Name:** Operation name (e.g., "generate_chat_response")
   - **Input:** What went in (truncated)
   - **Output:** What came out (truncated)
   - **Start Time:** When it happened
   - **Latency:** How long it took
   - **Tokens:** Token usage

3. **Click any row** to see full details

### Method 2: Filter by Tags

Use the filter/search bar to find specific operations:

- **Filter by tag:**
  - `tag:chat` - Only chat responses
  - `tag:rag` - Only RAG operations
  - `tag:embedding` - Only embedding operations
  - `tag:document_processing` - Only document processing

- **Filter by name:**
  - `name:generate_chat_response` - Only chat responses
  - `name:get_rag_context` - Only RAG context retrieval

- **Filter by error:**
  - `has_error:true` - Only failed operations

### Method 3: Search by Content

- **Search in inputs:** Type part of a user message
- **Search in outputs:** Type part of an AI response
- **Search by user:** `metadata.user_id:your-user-id`

### Method 4: View Trace Details

Click any trace to see:

#### **Input Section:**
- Full prompt/message sent
- All metadata (user_id, project_id, model, etc.)
- RAG context that was included

#### **Output Section:**
- Complete AI response
- Token breakdown (input/output/total)
- Model used
- Latency breakdown

#### **Child Runs:**
- Nested operations (e.g., RAG → Embedding → Vector Search)
- See the full execution tree

---

## 📈 Tracking Specific Outputs

### Track Chat Responses

1. **Filter:** `tag:chat` or `name:generate_chat_response`
2. **View Output column** - See truncated responses
3. **Click trace** - See full response
4. **Check metadata:**
   - `rag_document_context_count` - How many document chunks were used
   - `tokens_used` - Cost of this response
   - `model` - Which model was used

### Track RAG Performance

1. **Filter:** `tag:rag` or `name:get_rag_context`
2. **Check metadata:**
   - `document_context_count` - Documents retrieved
   - `user_context_count` - Previous messages retrieved
   - `global_context_count` - Knowledge patterns retrieved
3. **View Output:** See the combined context text sent to LLM

### Track Document Processing

1. **Filter:** `tag:document_processing` or `name:process_document`
2. **Check metadata:**
   - `filename` - Which document
   - `chunks_processed` - How many chunks created
   - `embeddings_created` - How many embeddings stored
3. **View Output:** Processing results and status

### Track Embedding Generation

1. **Filter:** `tag:embedding` or `name:generate_embedding`
2. **Check metadata:**
   - `text_length` - Length of text embedded
   - `dimension` - Embedding dimensions (1536)
   - `model` - Model used (text-embedding-3-small)
3. **View Output:** Embedding vector (truncated in UI)

---

## 🎨 Advanced Tracking Features

### 1. **Compare Traces**
- Select multiple traces
- Compare inputs/outputs side-by-side
- See what changed between runs

### 2. **View Execution Tree**
- Click a trace
- See "Child Runs" section
- Understand the full flow:
  ```
  generate_chat_response
    ├─ get_rag_context
    │   ├─ generate_query_embedding
    │   ├─ vector_search (document chunks)
    │   └─ vector_search (user messages)
    └─ openai.chat.completions.create
  ```

### 3. **Filter by Time Range**
- Use date picker in top right
- Filter by: Today, Last 7 days, Last 30 days, Custom range

### 4. **Export Data**
- Select traces
- Export to CSV/JSON
- Analyze in Excel/Python

### 5. **Set Up Alerts**
- Go to "Alerts" tab
- Create alerts for:
  - High error rates
  - Slow responses (>5s)
  - High token usage
  - Failed operations

---

## 🔎 Real-World Tracking Examples

### Example 1: "Why didn't the bot use my document?"

**Steps:**
1. Find the chat trace for that conversation
2. Click to view details
3. Check metadata: `rag_document_context_count`
   - If `0`: No documents retrieved → Check RAG trace
4. Look at child run: `get_rag_context`
5. Check its output: See if document chunks were found
6. Check its metadata: `document_context_count`

**Solution:**
- If RAG found 0 documents → Document not uploaded/processed
- If RAG found documents but not used → Check prompt construction

### Example 2: "This response cost too much"

**Steps:**
1. Filter: `tag:chat`
2. Sort by "Tokens" column (descending)
3. Click the expensive trace
4. Check:
   - `tokens_used` - Total tokens
   - `max_tokens` - Max tokens requested
   - `message_count` - How many messages in context
   - `rag_document_context_count` - How much context included

**Solution:**
- Reduce `max_tokens` in request
- Limit conversation history
- Reduce RAG context chunks

### Example 3: "Why is RAG so slow?"

**Steps:**
1. Filter: `name:get_rag_context`
2. Sort by "Latency" (descending)
3. Click slow traces
4. Check child runs:
   - `generate_query_embedding` - Embedding generation time
   - Vector search operations - Database query time
5. Compare with fast traces

**Solution:**
- Optimize embedding generation (batch if possible)
- Optimize vector search (indexes, similarity threshold)
- Cache frequently used queries

---

## 📊 Dashboard Stats

The **Stats** panel shows:
- **Run Count:** Total operations tracked
- **Total Tokens:** Cumulative token usage and cost
- **Error Rate:** Percentage of failed operations

Use this to:
- Monitor daily/weekly usage
- Track costs
- Identify reliability issues

---

## 🎯 Best Practices

1. **Use Tags:** Filter by `tag:chat` to see only chat operations
2. **Check Metadata:** Always check metadata for context counts, user IDs, etc.
3. **Compare Traces:** Compare successful vs failed traces to find patterns
4. **Monitor Trends:** Use time range filters to see trends over time
5. **Set Alerts:** Get notified when things go wrong

---

## 🆘 Troubleshooting

### No traces appearing?
- Check Vercel logs: Should see `[OK] LangSmith monitoring enabled`
- Verify `LANGSMITH_API_KEY` is set correctly
- Check you're looking at the right project name

### Can't see full outputs?
- Click the trace row to expand details
- Outputs are truncated in table view for performance
- Full outputs available in detail view

### Traces showing errors?
- Click the trace to see error details
- Check "Error" column in table view
- Filter by `has_error:true` to see all errors

---

## 💡 Pro Tips

1. **Bookmark Common Filters:**
   - `tag:chat` - All chat responses
   - `tag:rag` - All RAG operations
   - `has_error:true` - All errors

2. **Use Metadata Filters:**
   - `metadata.user_id:xxx` - Filter by user
   - `metadata.model:gpt-4o` - Filter by model

3. **Monitor Costs:**
   - Check "Tokens" column
   - Sort by tokens to find expensive operations
   - Use Stats panel for totals

4. **Debug Issues:**
   - Find the failing trace
   - Check child runs to see where it failed
   - Compare with successful traces

