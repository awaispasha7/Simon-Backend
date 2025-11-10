# RAG Test Questions and Vector Tracing

## Vector Database Tracing Added

I've added LangSmith tracing to all vector database operations. You should now see:

```
chat_generation (parent)
├── get_rag_context
│   ├── VectorStoreRetriever_user_messages
│   ├── VectorStoreRetriever_global_knowledge
│   └── VectorStoreRetriever_documents
├── ChatOpenAI (LLM call)
│   └── internet_search (if web search is used)
```

## Test Questions to Trigger RAG

Based on your system prompt, the chatbot is designed for **Simon's fitness coaching content creation**. Here are questions that should trigger RAG retrieval:

### 1. Brand Document Questions (Should trigger document retrieval)

**About Niche/Target Audience:**
- "Who is my niche?"
- "Who are my potential clients?"
- "Tell me about my target audience"
- "What is my ideal client profile?"

**About Tone/Style:**
- "What is my brand voice?"
- "How should I write my content?"
- "What tone should I use?"
- "Tell me about my writing style"

**About Scripts/Content:**
- "What are the best hooks for my content?"
- "How should I structure my scripts?"
- "What CTA formats should I use?"
- "Tell me about storytelling rules"
- "What are the content pillars?"

**About Brand Guidelines:**
- "What are my brand guidelines?"
- "What rules should I follow for content?"
- "How do I create carousel content?"

### 2. Questions That Should Trigger Vector Search

**Document-Specific:**
- "What does my Avatar Sheet say about my clients?"
- "According to my ICP document, who is my target audience?"
- "What are the script rules from my documents?"

**Content Creation:**
- "Create a script about [topic]"
- "Give me a hook for [topic]"
- "What CTA should I use for [topic]?"

### 3. Questions That May Not Trigger RAG

**General Questions (won't use documents):**
- "Hello"
- "How are you?"
- "What can you do?"
- "Tell me a joke"

**Questions Without Document Context:**
- "What is fitness?" (general knowledge, not brand-specific)
- "How do I lose weight?" (general advice, not brand-specific)

## Expected LangSmith Trace Structure

When you ask a RAG-triggering question, you should see:

```
chat_generation
├── get_rag_context
│   ├── VectorStoreRetriever_user_messages (searches message_embeddings)
│   ├── VectorStoreRetriever_global_knowledge (searches global_knowledge)
│   └── VectorStoreRetriever_documents (searches document_embeddings)
├── ChatOpenAI
│   └── [Response generation]
```

## How to Verify RAG is Working

1. **Check LangSmith Dashboard:**
   - Open a trace for a brand-related question
   - Expand `chat_generation`
   - You should see `get_rag_context` nested inside
   - Expand `get_rag_context` to see the three `VectorStoreRetriever` spans

2. **Check Trace Metadata:**
   - `VectorStoreRetriever_documents` should have:
     - `user_id`
     - `match_count`
     - `similarity_threshold`
     - `embedding_dimension: 1536`

3. **Check Logs:**
   - Look for: `"🔍 DocumentProcessor: Searching for document chunks"`
   - Look for: `"📚 Found X relevant document chunks"`

## Troubleshooting

If you don't see vector traces:

1. **Check if documents are uploaded:**
   - RAG only works if documents are uploaded and processed
   - Check if `document_embeddings` table has data

2. **Check if RAG is being called:**
   - Look for logs: `"[RAG] Getting RAG context for query"`
   - Check if `should_use_rag` is `True`

3. **Check LangSmith configuration:**
   - Verify `LANGSMITH_API_KEY` is set
   - Verify `LANGSMITH_PROJECT` is set
   - Check logs for any LangSmith errors

4. **Check trace nesting:**
   - Ensure all operations are within the `chat_generation` trace
   - `tracing_context` should automatically nest when called within an existing trace

## Best Test Questions

Start with these to ensure RAG is working:

1. **"Who is my niche?"** - Should retrieve from Avatar Sheet/ICP document
2. **"What are the best hooks?"** - Should retrieve from Script/Storytelling documents
3. **"What is my brand voice?"** - Should retrieve from North Star/Brand Vision documents
4. **"Create a script about [topic]"** - Should use all document types for context

These questions are specifically designed to match against your uploaded brand documents.

