"""
RAG (Retrieval Augmented Generation) Service
Combines embedding generation, vector search, and context building for LLM prompts
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from .embedding_service import get_embedding_service
from .vector_storage import vector_storage
from .document_processor import document_processor


class RAGService:
    """Service for RAG-enhanced chat responses"""
    
    def __init__(self):
        self.embedding_service = None  # Lazy initialization
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
        """Lazy initialization of embedding service"""
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()
        return self.embedding_service
    
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
        try:
            print(f"RAG: Building context for user {user_id}")
            
            # Step 1: Generate query embedding (include conversation context if available)
            if conversation_history:
                # Combine recent conversation for better context
                recent_context = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in conversation_history[-3:]
                ])
                query_text = f"{recent_context}\nUser: {user_message}"
            else:
                query_text = user_message
            
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
            
            # Step 4: Debug - Check if there are any document embeddings for this user (QUICK CHECK ONLY)
            try:
                from app.database.supabase import get_supabase_client
                supabase = get_supabase_client()
                print(f"🔍 [RAG] Quick check: Querying for user_id: {str(user_id)}")
                debug_result = supabase.table('document_embeddings').select('embedding_id', count='exact').eq('user_id', str(user_id)).limit(1).execute()
                count = debug_result.count if hasattr(debug_result, 'count') else len(debug_result.data) if debug_result.data else 0
                print(f"🔍 [RAG] Quick check: Found {count} document embeddings for user {user_id}")
            except Exception as e:
                print(f"🔍 [RAG] Quick check error: {e}")
            
            # Step 4: Retrieve document context
            # For personal assistant: search across all projects to maximize context
            # For multi-user: can limit by project_id if provided
            print(f"🔍 [RAG] Calling get_document_context")
            print(f"🔍 [RAG] user_id={user_id} (type: {type(user_id)}, str: {str(user_id)})")
            print(f"🔍 [RAG] project_id={project_id} (type: {type(project_id)})")
            print(f"🔍 [RAG] query_embedding length={len(query_embedding) if query_embedding else 'None'}")
            
            # Use very low threshold (0.1) to ensure we find documents
            # Vector similarity scores can be lower than expected even for relevant content
            document_context = []
            try:
                print(f"🔍 [RAG] Starting document retrieval...")
                document_context = await document_processor.get_document_context(
                    query_embedding=query_embedding,
                    user_id=user_id,
                    project_id=project_id,  # None = search all projects, specific ID = limit to that project
                    match_count=10,  # Increase match count to get more results
                    similarity_threshold=0.1  # Low threshold to ensure retrieval
                )
                print(f"✅ [RAG] Retrieved {len(document_context)} document chunks")
                if document_context:
                    print(f"✅ [RAG] First chunk preview: {document_context[0].get('chunk_text', '')[:200]}")
                    print(f"✅ [RAG] Document chunks will be included in AI context")
                else:
                    print(f"⚠️ [RAG] No document chunks retrieved - check if documents match query or threshold is too high")
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
            context_parts.append("This section contains information from uploaded brand documents including:")
            context_parts.append("- North Star / Brand Vision")
            context_parts.append("- ICP (Ideal Customer Profile) / Target Audience")
            context_parts.append("- Storytelling Rules & Guidelines")
            context_parts.append("- Hook Formulas & Structures")
            context_parts.append("- Content Pillars & Themes")
            context_parts.append("- Tone, Voice, and Writing Style Guidelines")
            context_parts.append("")
            context_parts.append("USE THIS INFORMATION TO ANSWER ALL BRAND-RELATED QUESTIONS.")
            context_parts.append("")
            for i, item in enumerate(document_context, 1):
                doc_type = item.get('document_type', 'unknown')
                chunk_text = item.get('chunk_text', '')
                similarity = item.get('similarity', 0)
                # Include MORE chunk text for better context (up to 800 chars for brand docs)
                context_parts.append(
                    f"{i}. [{doc_type.upper()}] (relevance: {similarity:.2f})\n{chunk_text[:800]}"
                )
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

