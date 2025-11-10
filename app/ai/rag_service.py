"""
RAG (Retrieval Augmented Generation) Service
Uses LangChain retrievers for automatic LangSmith tracing
"""

import os
from typing import List, Dict, Any, Optional
from uuid import UUID

# LangChain imports
try:
    from langchain_openai import OpenAIEmbeddings
    from .langchain_retrievers import (
        SupabaseMessageRetriever,
        SupabaseDocumentRetriever,
        SupabaseGlobalKnowledgeRetriever
    )
    from langchain_core.documents import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    OpenAIEmbeddings = None
    SupabaseMessageRetriever = None
    SupabaseDocumentRetriever = None
    SupabaseGlobalKnowledgeRetriever = None
    Document = None

# Fallback to old implementation if LangChain not available
if not LANGCHAIN_AVAILABLE:
    from .embedding_service import get_embedding_service
    from .vector_storage import vector_storage
    from .document_processor import document_processor

# LangSmith integration (for parent traces)
try:
    from .langsmith_config import create_trace
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def create_trace(*args, **kwargs):
        from contextlib import nullcontext
        return nullcontext()


class RAGService:
    """Service for RAG-enhanced chat responses"""
    
    def __init__(self):
        if LANGCHAIN_AVAILABLE:
            # Use LangChain embeddings (automatically traced)
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
        else:
            # Fallback to old implementation
            self.embedding_service = None
            self.vector_storage = vector_storage
        
        # Configuration for retrieval
        self.user_context_weight = 0.4  # 40% weight on user-specific context
        self.global_context_weight = 0.3  # 30% weight on global patterns (includes image analysis)
        self.document_context_weight = 0.3  # 30% weight on document context
        self.user_match_count = 6  # Retrieve top 6 similar user messages
        self.global_match_count = 3  # Retrieve top 3 global patterns (increased for image analysis)
        self.document_match_count = 3  # Retrieve top 3 document chunks
        self.similarity_threshold = 0.1  # Very low threshold for testing
    
    def _get_embedding_service(self):
        """Lazy initialization of embedding service (fallback only)"""
        if not LANGCHAIN_AVAILABLE:
            if self.embedding_service is None:
                self.embedding_service = get_embedding_service()
            return self.embedding_service
        return None
    
    def _expand_brand_query(self, query: str) -> str:
        """
        Expand queries to include relevant keywords based on document use cases
        This helps match against the right brand documents (Avatar Sheet, Script guides, etc.)
        
        Args:
            query: Original user query
            
        Returns:
            Expanded query with relevant keywords for document matching
        """
        query_lower = query.lower()
        
        # Map queries to specific document types
        # Avatar Sheet / ICP queries
        if any(phrase in query_lower for phrase in [
            "who are my", "who is my", "my niche", "my audience", "my target", "potential clients",
            "ideal customer", "target audience", "who do i", "who should i"
        ]):
            return f"{query} avatar sheet ICP ideal customer profile target audience potential clients niche demographics psychographics"
        
        # Script/Storytelling queries
        if any(phrase in query_lower for phrase in [
            "script", "hook", "cta", "story", "video", "content", "create", "write", "generate"
        ]):
            return f"{query} script structure hook formulas CTA call to action storytelling rules content creation"
        
        # Tone/Style queries
        if any(phrase in query_lower for phrase in [
            "tone", "voice", "style", "how do i write", "writing style", "how should i"
        ]):
            return f"{query} tone voice writing style brand identity north star brand vision"
        
        # Content strategy queries
        if any(phrase in query_lower for phrase in [
            "content strategy", "weekly", "ideas", "plan", "calendar", "content plan"
        ]):
            return f"{query} content strategy content pillars weekly planning content ideas"
        
        # Carousel queries
        if any(phrase in query_lower for phrase in [
            "carousel", "slides", "post", "instagram post"
        ]):
            return f"{query} carousel rules carousel structure slides headline"
        
        # General personal/brand queries
        if any(phrase in query_lower for phrase in [
            "what do you know about me", "who am i", "what's my", "what is my",
            "tell me about me", "my brand"
        ]):
            return f"{query} niche target audience ICP ideal customer profile brand identity tone voice writing style content pillars storytelling rules hook formulas CTA call to action"
        
        return query
    
    async def get_rag_context(
        self,
        user_message: str,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Get RAG context for a user message
        
        Args:
            user_message: Current user message
            user_id: ID of the user
            project_id: Optional project ID
            conversation_history: Optional recent conversation history
            
        Returns:
            Dict containing:
            - user_context: Relevant user-specific messages
            - global_context: Relevant global knowledge patterns
            - combined_context_text: Formatted context for LLM prompt
            - metadata: Metadata about retrieval
        """
        # LangSmith tracing for RAG operations
        with create_trace(
            name="get_rag_context",
            run_type="chain",
            tags=["rag", "retrieval", "context_building"],
            metadata={
                "user_id": str(user_id),
                "project_id": str(project_id) if project_id else None,
                "user_message_length": len(user_message),
                "has_conversation_history": bool(conversation_history),
                "conversation_history_length": len(conversation_history) if conversation_history else 0
            }
        ):
            try:
                print(f"RAG: Building context for user {user_id}")
                
                # Step 1: Generate query embedding (include conversation context if available)
                # CRITICAL: Expand generic queries about "me" or "my" to include brand-related keywords
                # This helps match against brand documents (niche, ICP, tone, etc.) instead of irrelevant docs
                expanded_query = self._expand_brand_query(user_message)
                
                if conversation_history:
                    # Combine recent conversation for better context
                    recent_context = "\n".join([
                        f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                        for msg in conversation_history[-3:]
                    ])
                    query_text = f"{recent_context}\nUser: {expanded_query}"
                else:
                    query_text = expanded_query
                
                # Step 2: Retrieve context using LangChain retrievers (automatically traced)
                if LANGCHAIN_AVAILABLE:
                    # Use LangChain retrievers - automatically traced by LangSmith
                    message_retriever = SupabaseMessageRetriever(
                        user_id=user_id,
                        project_id=project_id,
                        k=self.user_match_count,
                        score_threshold=self.similarity_threshold
                    )
                    
                    global_retriever = SupabaseGlobalKnowledgeRetriever(
                        k=self.global_match_count,
                        score_threshold=self.similarity_threshold,
                        min_quality_score=0.6
                    )
                    
                    document_retriever = SupabaseDocumentRetriever(
                        user_id=user_id,
                        project_id=project_id,
                        k=self.document_match_count,
                        score_threshold=self.similarity_threshold
                    )
                    
                    # Retrieve documents (these calls are automatically traced)
                    user_docs = message_retriever.get_relevant_documents(query_text)
                    global_docs = global_retriever.get_relevant_documents(query_text)
                    document_docs = document_retriever.get_relevant_documents(query_text)
                    
                    # Convert LangChain Documents to our format
                    user_context = [
                        {
                            'content_snippet': doc.page_content,
                            'message_id': doc.metadata.get('message_id'),
                            'user_id': doc.metadata.get('user_id'),
                            'project_id': doc.metadata.get('project_id'),
                            'session_id': doc.metadata.get('session_id'),
                            'role': doc.metadata.get('role'),
                            'similarity': doc.metadata.get('similarity', 0.0),
                            'metadata': {k: v for k, v in doc.metadata.items() if k not in ['message_id', 'user_id', 'project_id', 'session_id', 'role', 'similarity']}
                        }
                        for doc in user_docs
                    ]
                    
                    global_context = [
                        {
                            'example_text': doc.page_content,
                            'knowledge_id': doc.metadata.get('knowledge_id'),
                            'category': doc.metadata.get('category'),
                            'pattern_type': doc.metadata.get('pattern_type'),
                            'description': doc.metadata.get('description'),
                            'quality_score': doc.metadata.get('quality_score', 0.0),
                            'similarity': doc.metadata.get('similarity', 0.0),
                            'tags': doc.metadata.get('tags', []),
                            'metadata': {k: v for k, v in doc.metadata.items() if k not in ['knowledge_id', 'category', 'pattern_type', 'description', 'quality_score', 'similarity', 'tags']}
                        }
                        for doc in global_docs
                    ]
                    
                    document_context = [
                        {
                            'chunk_text': doc.page_content,
                            'embedding_id': doc.metadata.get('embedding_id'),
                            'asset_id': doc.metadata.get('asset_id'),
                            'user_id': doc.metadata.get('user_id'),
                            'project_id': doc.metadata.get('project_id'),
                            'document_type': doc.metadata.get('document_type'),
                            'chunk_index': doc.metadata.get('chunk_index'),
                            'similarity': doc.metadata.get('similarity', 0.0),
                            'metadata': {k: v for k, v in doc.metadata.items() if k not in ['embedding_id', 'asset_id', 'user_id', 'project_id', 'document_type', 'chunk_index', 'similarity']}
                        }
                        for doc in document_docs
                    ]
                else:
                    # Fallback to old implementation
                    query_embedding = await self._get_embedding_service().generate_query_embedding(query_text)
                    
                    # Step 2: Retrieve user-specific context
                    user_context = await self.vector_storage.get_similar_user_messages(
                        query_embedding=query_embedding,
                        user_id=user_id,
                        project_id=project_id,
                        match_count=self.user_match_count,
                        similarity_threshold=self.similarity_threshold
                    )
                    
                    # Step 3: Retrieve global knowledge patterns
                    global_context = await self.vector_storage.get_similar_global_knowledge(
                        query_embedding=query_embedding,
                        match_count=self.global_match_count,
                        similarity_threshold=self.similarity_threshold,
                        min_quality_score=0.6
                    )
                
                # Step 4: Document context already retrieved above if using LangChain
                if not LANGCHAIN_AVAILABLE:
                    # Fallback: Retrieve document context using old method
                    print(f"🔍 [RAG] Calling get_document_context (fallback)")
                    document_context = []
                    try:
                        print(f"🔍 [RAG] Starting document retrieval...")
                        document_context = await document_processor.get_document_context(
                            query_embedding=query_embedding,
                            user_id=user_id,
                            project_id=project_id,
                            match_count=10,
                            similarity_threshold=0.1
                        )
                        print(f"✅ [RAG] Retrieved {len(document_context)} document chunks")
                    except Exception as doc_error:
                        print(f"❌ [RAG] Error retrieving document context: {doc_error}")
                        import traceback
                        print(traceback.format_exc())
                        document_context = []
                
                # Step 5: Build combined context text for LLM prompt
                combined_context_text = self._format_rag_context(user_context, global_context, document_context)
                
                # Step 6: Build metadata
                metadata = {
                    "user_context_count": len(user_context),
                    "global_context_count": len(global_context),
                    "document_context_count": len(document_context),
                    "query_length": len(user_message),
                    "has_conversation_history": bool(conversation_history)
                }
                
                print(f"📊 [RAG] Final summary: {len(user_context)} user contexts, {len(global_context)} global patterns, {len(document_context)} document chunks")
                print(f"📊 [RAG] Combined context text length: {len(combined_context_text)} chars")
                if combined_context_text:
                    print(f"📊 [RAG] Combined context preview (first 300 chars): {combined_context_text[:300]}...")
                if document_context:
                    print(f"✅ [RAG] SUCCESS: Document context will be included in AI prompt!")
                    print(f"✅ [RAG] Document chunks in context: {len(document_context)}")
                else:
                    print(f"⚠️ [RAG] WARNING: No document context retrieved - AI won't have document information")
                
                return {
                    "user_context": user_context,
                    "global_context": global_context,
                    "document_context": document_context,
                    "combined_context_text": combined_context_text,
                    "metadata": metadata
                }
                
            except Exception as e:
                print(f"ERROR: Failed to get RAG context: {e}")
                return {
                    "user_context": [],
                    "global_context": [],
                    "document_context": [],
                    "combined_context_text": "",
                    "metadata": {"error": str(e)}
                }
    
    def _format_rag_context(
        self,
        user_context: List[Dict[str, Any]],
        global_context: List[Dict[str, Any]],
        document_context: List[Dict[str, Any]]
    ) -> str:
        """
        Format retrieved context into a prompt-friendly string
        
        Args:
            user_context: User-specific messages
            global_context: Global knowledge patterns
            document_context: Document chunks
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add user-specific context
        if user_context:
            context_parts.append("## Relevant Context from Your Previous Conversations:")
            for i, item in enumerate(user_context[:5], 1):  # Limit to top 5
                role = item.get('role', 'unknown')
                content = item.get('content', '')
                similarity = item.get('similarity', 0)
                context_parts.append(f"{i}. [{role.upper()}] (relevance: {similarity:.2f}) {content[:200]}...")
            context_parts.append("")
        
        # Add document context - CRITICAL: This is the brand documents (North Star, ICP, rules, etc.)
        if document_context:
            context_parts.append("## 🔴 BRAND DOCUMENTS - CRITICAL INFORMATION:")
            context_parts.append("")
            context_parts.append("YOU MUST USE THIS INFORMATION TO ANSWER ALL QUESTIONS ABOUT:")
            context_parts.append("- Brand identity, niche, target audience, potential clients")
            context_parts.append("- Tone, voice, writing style, sentence rhythm, emotional pacing")
            context_parts.append("- Storytelling rules, hook formulas, content pillars")
            context_parts.append("- Script structure, CTA formats, carousel rules")
            context_parts.append("- Audience fears, desires, struggles")
            context_parts.append("")
            context_parts.append("DOCUMENT USE CASES:")
            context_parts.append("- Avatar Sheet / ICP Document: Use for questions about potential clients, target audience, niche")
            context_parts.append("- Script/Storytelling Documents: Use for script creation, hooks, CTAs, storytelling structure")
            context_parts.append("- Content Strategy Documents: Use for content ideas, weekly planning, content pillars")
            context_parts.append("- Carousel Documents: Use for carousel creation rules and structure")
            context_parts.append("- North Star / Brand Vision: Use for brand identity, tone, voice, overall approach")
            context_parts.append("")
            context_parts.append("WHEN ANSWERING QUESTIONS:")
            context_parts.append("1. If asked about niche/clients/audience → Use Avatar Sheet / ICP document")
            context_parts.append("2. If asked to create scripts → Use Script/Storytelling documents for structure and rules")
            context_parts.append("3. If asked about tone/style → Use North Star / Brand Vision documents")
            context_parts.append("4. If asked about content strategy → Use Content Strategy documents")
            context_parts.append("5. ALWAYS apply the rules and guidelines from these documents to your outputs")
            context_parts.append("")
            context_parts.append("DOCUMENT CONTENT:")
            for i, item in enumerate(document_context, 1):
                doc_type = item.get('document_type', 'unknown')
                chunk_text = item.get('chunk_text', '')
                similarity = item.get('similarity', 0)
                metadata = item.get('metadata', {})
                filename = metadata.get('filename', 'Unknown Document')
                
                # Include document filename to help AI understand which document this is
                context_parts.append(f"--- Document {i}: {filename} ({doc_type.upper()}, relevance: {similarity:.2f}) ---")
                # Include MORE chunk text for better context (up to 1000 chars for brand docs)
                context_parts.append(chunk_text[:1000])
                context_parts.append("")
            context_parts.append("")
            context_parts.append("REMEMBER: This information is from Simon's uploaded brand documents. Use it directly to answer questions.")
            context_parts.append("")
        
        # Add global knowledge context
        if global_context:
            context_parts.append("## Relevant Storytelling Patterns and Knowledge:")
            for i, item in enumerate(global_context, 1):
                category = item.get('category', 'general')
                pattern = item.get('pattern_type', 'unknown')
                example = item.get('example_text', '')
                similarity = item.get('similarity', 0)
                context_parts.append(
                    f"{i}. [{category}/{pattern}] (relevance: {similarity:.2f}) {example[:150]}..."
                )
            context_parts.append("")
        
        if not context_parts:
            return ""
        
        return "\n".join(context_parts)
    
    async def embed_and_store_message(
        self,
        message_id: UUID,
        user_id: UUID,
        project_id: UUID,
        session_id: UUID,
        content: str,
        role: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Generate and store embedding for a message
        
        Args:
            message_id: ID of the message
            user_id: ID of the user
            project_id: ID of the project
            session_id: ID of the session
            content: Message content
            role: Message role
            metadata: Optional metadata
            
        Returns:
            True if successful, False otherwise
        """
        # LangSmith tracing
        with create_trace(
            name="embed_and_store_message",
            run_type="chain",
            tags=["rag", "embedding", "storage"],
            metadata={
                "message_id": str(message_id),
                "user_id": str(user_id),
                "project_id": str(project_id),
                "session_id": str(session_id),
                "role": role,
                "content_length": len(content)
            }
        ):
            try:
                # Generate embedding
                embedding = await self._get_embedding_service().generate_embedding(content)
                
                # Store embedding
                embedding_id = await self.vector_storage.store_message_embedding(
                    message_id=message_id,
                    user_id=user_id,
                    project_id=project_id,
                    session_id=session_id,
                    embedding=embedding,
                    content=content,
                    role=role,
                    metadata=metadata
                )
                
                return embedding_id is not None
                
            except Exception as e:
                print(f"ERROR: Failed to embed and store message: {e}")
                return False
    
    async def extract_and_store_knowledge(
        self,
        conversation: List[Dict[str, str]],
        user_id: UUID,
        project_id: UUID
    ):
        """
        Extract knowledge patterns from a conversation and store in global knowledge base
        This is called after successful conversations to build the knowledge base
        
        Args:
            conversation: List of messages in the conversation
            user_id: ID of the user (for attribution, not stored in global KB)
            project_id: ID of the project
        """
        # LangSmith tracing
        with create_trace(
            name="extract_and_store_knowledge",
            run_type="chain",
            tags=["rag", "knowledge_extraction", "storage"],
            metadata={
                "user_id": str(user_id),
                "project_id": str(project_id),
                "conversation_length": len(conversation)
            }
        ):
            try:
                print(f"RAG: Extracting knowledge from conversation (user: {user_id})")
                
                # Analyze conversation for patterns
                # This is a simplified version - you can make this more sophisticated
                
                # Example: Extract character development patterns
                character_mentions = self._extract_character_patterns(conversation)
                for char_pattern in character_mentions:
                    embedding = await self._get_embedding_service().generate_embedding(char_pattern['text'])
                    await self.vector_storage.store_global_knowledge(
                        category='character',
                        pattern_type='character_development',
                        embedding=embedding,
                        example_text=char_pattern['text'],
                        description=char_pattern.get('description'),
                        quality_score=0.7,
                        tags=['conversation_extracted']
                    )
                
                # Example: Extract plot patterns
                plot_patterns = self._extract_plot_patterns(conversation)
                for plot_pattern in plot_patterns:
                    embedding = await self._get_embedding_service().generate_embedding(plot_pattern['text'])
                    await self.vector_storage.store_global_knowledge(
                        category='plot',
                        pattern_type='story_arc',
                        embedding=embedding,
                        example_text=plot_pattern['text'],
                        description=plot_pattern.get('description'),
                        quality_score=0.7,
                        tags=['conversation_extracted']
                    )
                
                print(f"RAG: Extracted {len(character_mentions)} character patterns, {len(plot_patterns)} plot patterns")
                
            except Exception as e:
                print(f"ERROR: Failed to extract and store knowledge: {e}")
    
    def _extract_character_patterns(self, conversation: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Extract character-related patterns from conversation"""
        patterns = []
        # Simplified extraction - look for character-related keywords
        keywords = ['character', 'protagonist', 'antagonist', 'hero', 'villain']
        
        for msg in conversation:
            content = msg.get('content', '').lower()
            if any(keyword in content for keyword in keywords):
                patterns.append({
                    'text': msg.get('content', '')[:500],
                    'description': 'Character discussion pattern'
                })
        
        return patterns[:3]  # Limit to 3 patterns
    
    def _extract_plot_patterns(self, conversation: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Extract plot-related patterns from conversation"""
        patterns = []
        # Simplified extraction - look for plot-related keywords
        keywords = ['plot', 'story', 'conflict', 'resolution', 'climax', 'arc']
        
        for msg in conversation:
            content = msg.get('content', '').lower()
            if any(keyword in content for keyword in keywords):
                patterns.append({
                    'text': msg.get('content', '')[:500],
                    'description': 'Plot development pattern'
                })
        
        return patterns[:3]  # Limit to 3 patterns


# Global singleton instance
rag_service = RAGService()

