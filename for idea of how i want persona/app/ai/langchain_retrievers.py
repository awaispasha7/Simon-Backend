"""
LangChain Custom Retrievers for Supabase RPC Functions
These retrievers extend LangChain's BaseRetriever to get automatic LangSmith tracing
"""

import os
from typing import List, Optional, Dict, Any
from uuid import UUID

# LangChain imports
try:
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.documents import Document
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    from langchain_openai import OpenAIEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    BaseRetriever = None
    Document = None
    CallbackManagerForRetrieverRun = None
    OpenAIEmbeddings = None
    print(f"[WARN] LangChain not available: {e}")

# LangSmith tracing (explicit for custom retrievers)
try:
    from langsmith import traceable
    LANGSMITH_TRACEABLE_AVAILABLE = True
except ImportError:
    LANGSMITH_TRACEABLE_AVAILABLE = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from ..database.supabase import get_supabase_client


class SupabaseMessageRetriever(BaseRetriever):
    """
    Custom LangChain retriever for Supabase message embeddings
    Automatically traced by LangSmith when LANGSMITH_TRACING=true
    """
    
    def __init__(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        k: int = 10,
        score_threshold: float = 0.7,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.project_id = project_id
        self.k = k
        self.score_threshold = score_threshold
        self.supabase = get_supabase_client()
        
        # Initialize embeddings for query embedding generation
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        ) if LANGCHAIN_AVAILABLE else None
    
    @traceable(
        run_type="retriever",
        name="SupabaseMessageRetriever"
    )
    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """
        Retrieve relevant documents from Supabase message_embeddings table
        This method is automatically traced by LangSmith (via BaseRetriever and @traceable)
        """
        if not self.supabase or not self.embeddings:
            print(f"[WARN] SupabaseMessageRetriever: Missing supabase client or embeddings")
            return []
        
        try:
            print(f"[RAG] SupabaseMessageRetriever: Generating embedding for query: {query[:50]}...")
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            print(f"[RAG] SupabaseMessageRetriever: Embedding generated, length: {len(query_embedding)}")
            
            # Call Supabase RPC function
            print(f"[RAG] SupabaseMessageRetriever: Calling Supabase RPC...")
            result = self.supabase.rpc(
                'get_similar_user_messages',
                {
                    'query_embedding': query_embedding,
                    'query_user_id': str(self.user_id),
                    'query_project_id': str(self.project_id) if self.project_id else None,
                    'match_count': self.k,
                    'similarity_threshold': self.score_threshold
                }
            ).execute()
            
            # Convert to LangChain Documents
            documents = []
            if result.data:
                print(f"[RAG] SupabaseMessageRetriever: Found {len(result.data)} results")
                for item in result.data:
                    doc = Document(
                        page_content=item.get('content_snippet', ''),
                        metadata={
                            'message_id': item.get('message_id'),
                            'user_id': item.get('user_id'),
                            'project_id': item.get('project_id'),
                            'session_id': item.get('session_id'),
                            'role': item.get('role'),
                            'similarity': item.get('similarity', 0.0),
                            **(item.get('metadata', {}) or {})
                        }
                    )
                    documents.append(doc)
            else:
                print(f"[RAG] SupabaseMessageRetriever: No results found")
            
            return documents
            
        except Exception as e:
            print(f"ERROR: SupabaseMessageRetriever failed: {e}")
            import traceback
            print(traceback.format_exc())
            return []
    
    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """Async version - same implementation"""
        # For now, use sync version (LangChain handles async internally)
        return self._get_relevant_documents(query, run_manager=run_manager)


class SupabaseDocumentRetriever(BaseRetriever):
    """
    Custom LangChain retriever for Supabase document embeddings
    Automatically traced by LangSmith when LANGSMITH_TRACING=true
    """
    
    def __init__(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        k: int = 5,
        score_threshold: float = 0.7,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.project_id = project_id
        self.k = k
        self.score_threshold = score_threshold
        self.supabase = get_supabase_client()
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        ) if LANGCHAIN_AVAILABLE else None
    
    @traceable(
        run_type="retriever",
        name="SupabaseDocumentRetriever"
    )
    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """
        Retrieve relevant documents from Supabase document_embeddings table
        This method is automatically traced by LangSmith (via BaseRetriever and @traceable)
        """
        if not self.supabase or not self.embeddings:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Call Supabase RPC function
            result = self.supabase.rpc(
                'get_similar_document_chunks',
                {
                    'query_embedding': query_embedding,
                    'query_user_id': str(self.user_id),
                    'query_project_id': str(self.project_id) if self.project_id else None,
                    'match_count': self.k,
                    'similarity_threshold': self.score_threshold
                }
            ).execute()
            
            # Convert to LangChain Documents
            documents = []
            if result.data:
                for item in result.data:
                    doc = Document(
                        page_content=item.get('chunk_text', ''),
                        metadata={
                            'embedding_id': item.get('embedding_id'),
                            'asset_id': item.get('asset_id'),
                            'user_id': item.get('user_id'),
                            'project_id': item.get('project_id'),
                            'document_type': item.get('document_type'),
                            'chunk_index': item.get('chunk_index'),
                            'similarity': item.get('similarity', 0.0),
                            **(item.get('metadata', {}) or {})
                        }
                    )
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"ERROR: SupabaseDocumentRetriever failed: {e}")
            return []
    
    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """Async version"""
        return self._get_relevant_documents(query, run_manager=run_manager)


class SupabaseGlobalKnowledgeRetriever(BaseRetriever):
    """
    Custom LangChain retriever for Supabase global_knowledge table
    Automatically traced by LangSmith when LANGSMITH_TRACING=true
    """
    
    def __init__(
        self,
        k: int = 5,
        score_threshold: float = 0.7,
        min_quality_score: float = 0.6,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.k = k
        self.score_threshold = score_threshold
        self.min_quality_score = min_quality_score
        self.supabase = get_supabase_client()
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        ) if LANGCHAIN_AVAILABLE else None
    
    @traceable(
        run_type="retriever",
        name="SupabaseGlobalKnowledgeRetriever"
    )
    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """
        Retrieve relevant documents from Supabase global_knowledge table
        This method is automatically traced by LangSmith (via BaseRetriever and @traceable)
        """
        if not self.supabase or not self.embeddings:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Call Supabase RPC function
            result = self.supabase.rpc(
                'get_similar_global_knowledge',
                {
                    'query_embedding': query_embedding,
                    'match_count': self.k,
                    'similarity_threshold': self.score_threshold,
                    'min_quality_score': self.min_quality_score
                }
            ).execute()
            
            # Convert to LangChain Documents
            documents = []
            if result.data:
                for item in result.data:
                    doc = Document(
                        page_content=item.get('example_text', '') or item.get('description', ''),
                        metadata={
                            'knowledge_id': item.get('knowledge_id'),
                            'category': item.get('category'),
                            'pattern_type': item.get('pattern_type'),
                            'description': item.get('description'),
                            'quality_score': item.get('quality_score', 0.0),
                            'similarity': item.get('similarity', 0.0),
                            'tags': item.get('tags', []),
                            **(item.get('metadata', {}) or {})
                        }
                    )
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"ERROR: SupabaseGlobalKnowledgeRetriever failed: {e}")
            return []
    
    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """Async version"""
        return self._get_relevant_documents(query, run_manager=run_manager)

