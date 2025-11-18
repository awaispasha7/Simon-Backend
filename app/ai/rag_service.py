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
        # Always query from ALL sources - let similarity search determine relevance
        # Higher match counts ensure we don't miss relevant information
        # Increased counts to capture personal info even with lower similarity scores
        self.user_match_count = 30  # Retrieve from user messages
        self.global_match_count = 50  # Retrieve from global knowledge (training data, "About Me", etc.) - increased to capture personal info
        self.document_match_count = 20  # Retrieve from user-uploaded documents
        self.similarity_threshold = 0.05  # Broader net to avoid misses
        
        # Display limits (to avoid token bloat, but we retrieve more to have options)
        # The most relevant items (by similarity) will naturally float to the top
        self.max_display_items = 40  # Total items to show in prompt (most relevant from all sources) - increased to include more personal info
    
    def _get_embedding_service(self):
        """Lazy initialization of embedding service"""
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()
        return self.embedding_service
    
    async def get_rag_context(
        self,
        user_message: str,
        user_id: UUID,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Get RAG context for a user message
        
        Args:
            user_message: Current user message
            user_id: ID of the user
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
            # Enhance query for personal information queries to improve retrieval
            user_message_lower = user_message.lower()
            is_personal_query = any(phrase in user_message_lower for phrase in [
                "do you know about me", "tell me about myself", "who am i", "about me",
                "what do you know", "my information", "personal information",
                "do you know who", "who is", "tell me about", "simon"
            ])
            
            if conversation_history:
                # Combine recent conversation for better context
                recent_context = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in conversation_history[-5:]  # include last 5 turns
                ])
                query_text = f"{recent_context}\nUser: {user_message}"
            else:
                query_text = user_message
            
            # Enhance query for personal information to improve semantic matching
            if is_personal_query:
                # Add context keywords that would match personal info content
                query_text = f"{query_text} personal information about the user coaching health fitness weight loss liposuction Simon Boberg"
                print(f"🔍 [RAG] Personal query detected - enhanced query: {query_text[:200]}...")
            
            query_embedding = await self._get_embedding_service().generate_query_embedding(query_text)
            
            # Step 2: Retrieve user-specific context
            # Search across all user messages (session_id=None) for broader context
            user_context = await self.vector_storage.get_similar_user_messages(
                query_embedding=query_embedding,
                user_id=user_id,
                session_id=None,  # Search across all sessions for broader context
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
            
            # Step 4: Debug - Check if there are any document embeddings for this user
            try:
                from app.database.supabase import get_supabase_client
                supabase = get_supabase_client()
                print(f"🔍 RAG Debug: Querying for user_id: {str(user_id)} (type: {type(user_id)})")
                debug_result = supabase.table('document_embeddings').select('*').eq('user_id', str(user_id)).execute()
                print(f"🔍 RAG Debug: Found {len(debug_result.data)} document embeddings for user {user_id}")
                
                # Also check all embeddings to see what's in the database
                all_embeddings = supabase.table('document_embeddings').select('user_id, asset_id, document_type').execute()
                print(f"🔍 RAG Debug: Total embeddings in database: {len(all_embeddings.data)}")
                for row in all_embeddings.data:
                    print(f"  - User: {row.get('user_id')}, Asset: {row.get('asset_id')}, Type: {row.get('document_type')}")
                
                if debug_result.data:
                    for row in debug_result.data:
                        print(f"  - Asset: {row.get('asset_id')}, Type: {row.get('document_type')}")
            except Exception as e:
                print(f"🔍 RAG Debug: Error checking embeddings: {e}")
            
            # Step 4: Retrieve document context (projects no longer supported)
            print(f"🔍 RAG: Calling get_document_context with user_id: {user_id} (type: {type(user_id)})")
            document_context = await document_processor.get_document_context(
                query_embedding=query_embedding,
                user_id=user_id,
                match_count=self.document_match_count,
                similarity_threshold=self.similarity_threshold
            )
            
            # Step 5: Debug - Log what we actually retrieved
            if global_context:
                print(f"🔍 [RAG DEBUG] Sample global_context item keys: {list(global_context[0].keys()) if global_context else 'N/A'}")
                print(f"🔍 [RAG DEBUG] Sample global_context item: {global_context[0] if global_context else 'N/A'}")
            if user_context:
                print(f"🔍 [RAG DEBUG] Sample user_context item keys: {list(user_context[0].keys()) if user_context else 'N/A'}")
            
            # Step 5: Build combined context text for LLM prompt
            combined_context_text = self._format_rag_context(user_context, global_context, document_context)
            
            print(f"🔍 [RAG DEBUG] Formatted context text length: {len(combined_context_text)} chars")
            if combined_context_text:
                print(f"🔍 [RAG DEBUG] Formatted context preview: {combined_context_text[:500]}...")
                # Check if personal info is in the context
                context_lower = combined_context_text.lower()
                has_simon = "simon" in context_lower or "boberg" in context_lower
                has_coaching = "coaching" in context_lower
                has_personal = "personal" in context_lower or "about me" in context_lower
                print(f"🔍 [RAG DEBUG] Context check - Simon/Boberg: {has_simon}, Coaching: {has_coaching}, Personal: {has_personal}")
                
                # Show top 5 global items to see what's being included
                if global_context:
                    print(f"🔍 [RAG DEBUG] Top 5 global knowledge items by similarity:")
                    for i, item in enumerate(global_context[:5], 1):
                        tags = item.get('tags', [])
                        similarity = item.get('similarity', 0)
                        preview = (item.get('example_text', '') or item.get('description', ''))[:150]
                        print(f"  {i}. Similarity: {similarity:.3f}, Tags: {tags}, Preview: {preview}...")
            
            # Step 6: Build metadata
            metadata = {
                "user_context_count": len(user_context),
                "global_context_count": len(global_context),
                "document_context_count": len(document_context),
                "query_length": len(user_message),
                "has_conversation_history": bool(conversation_history)
            }
            
            print(f"RAG: Retrieved {len(user_context)} user contexts, {len(global_context)} global patterns, {len(document_context)} document chunks")
            
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
        Combines ALL sources and sorts by similarity (most relevant first)
        
        Args:
            user_context: User-specific messages
            global_context: Global knowledge patterns
            document_context: Document chunks
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Combine all sources into a unified list with source type
        all_items = []
        
        # Add user context items
        for item in user_context:
            content = item.get('content', '') or item.get('content_snippet', '')
            if content.strip():
                all_items.append({
                    'source': 'user',
                    'similarity': item.get('similarity', 0),
                    'content': content,
                    'role': item.get('role', 'unknown'),
                    'metadata': item
                })
        
        # Add document context items
        for item in document_context:
            chunk_text = item.get('chunk_text', '')
            if chunk_text.strip():
                all_items.append({
                    'source': 'document',
                    'similarity': item.get('similarity', 0),
                    'content': chunk_text,
                    'doc_type': item.get('document_type', 'unknown'),
                    'metadata': item
                })
        
        # Add global knowledge items (but filter out personal info since it's in system prompt)
        for item in global_context:
            example = item.get('example_text', '') or item.get('description', '') or ''
            if example.strip():
                # Skip personal info chunks - they're already in the system prompt
                tags = item.get('tags', [])
                example_lower = example.lower()
                is_personal_info = (
                    any('personal' in str(tag).lower() for tag in tags) or
                    any('about me' in str(tag).lower() for tag in tags) or
                    'simon boberg' in example_lower or
                    'simon@simonbobergcoaching.com' in example_lower or
                    ('coaching' in example_lower and 'liposuction' in example_lower and len(example) > 500)  # Long coaching content
                )
                
                if not is_personal_info:
                    all_items.append({
                        'source': 'global',
                        'similarity': item.get('similarity', 0),
                        'content': example,
                        'category': item.get('category', 'general'),
                        'pattern_type': item.get('pattern_type', 'unknown'),
                        'tags': item.get('tags', []),
                        'metadata': item
                    })
                else:
                    print(f"🔍 [RAG] Filtered out personal info chunk (already in system prompt): {item.get('tags', [])}")
        
        # Sort ALL items by similarity (highest first) - most relevant items naturally float to top
        all_items.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        # Take top N most relevant items regardless of source
        top_items = all_items[:self.max_display_items]
        
        if not top_items:
            return ""
        
        # Group by source for display organization, but items are already sorted by similarity
        user_items = [item for item in top_items if item['source'] == 'user']
        doc_items = [item for item in top_items if item['source'] == 'document']
        global_items = [item for item in top_items if item['source'] == 'global']
        
        # Display sources in order of their highest similarity item (most relevant source first)
        source_groups = []
        if global_items:
            max_global_sim = max([item['similarity'] for item in global_items])
            source_groups.append(('global', global_items, max_global_sim))
        if doc_items:
            max_doc_sim = max([item['similarity'] for item in doc_items])
            source_groups.append(('document', doc_items, max_doc_sim))
        if user_items:
            max_user_sim = max([item['similarity'] for item in user_items])
            source_groups.append(('user', user_items, max_user_sim))
        
        # Sort sources by their highest similarity item
        source_groups.sort(key=lambda x: x[2], reverse=True)
        
        # Format each source group
        for source_type, items, _max_sim in source_groups:
            if not items:
                continue
            
            if source_type == 'global':
                context_parts.append("## Relevant Knowledge:")
                for i, item in enumerate(items, 1):
                    category = item.get('category', 'general')
                    pattern = item.get('pattern_type', 'unknown')
                    content = item['content']
                    similarity = item['similarity']
                    context_parts.append(
                        f"{i}. [{category}/{pattern}] (relevance: {similarity:.2f}) {content[:250]}..."
                    )
                context_parts.append("")
            
            elif source_type == 'document':
                context_parts.append("## Relevant Documents:")
                for i, item in enumerate(items, 1):
                    doc_type = item.get('doc_type', 'unknown')
                    content = item['content']
                    similarity = item['similarity']
                    context_parts.append(
                        f"{i}. [{doc_type.upper()}] (relevance: {similarity:.2f}) {content[:250]}..."
                    )
                context_parts.append("")
            
            elif source_type == 'user':
                context_parts.append("## Relevant Conversations:")
                for i, item in enumerate(items, 1):
                    role = item.get('role', 'unknown')
                    content = item['content']
                    similarity = item['similarity']
                    context_parts.append(
                        f"{i}. [{role.upper()}] (relevance: {similarity:.2f}) {content[:200]}..."
                    )
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    async def embed_and_store_message(
        self,
        message_id: UUID,
        user_id: UUID,
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
            
            # Store embedding (project_id removed - projects no longer supported)
            embedding_id = await self.vector_storage.store_message_embedding(
                message_id=message_id,
                user_id=user_id,
                project_id=None,  # Projects no longer supported
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

