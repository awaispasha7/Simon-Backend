"""
LangChain-based Vector Storage Service
Uses LangChain's SupabaseVectorStore for automatic LangSmith tracing
"""

import os
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

# LangChain imports
try:
    from langchain_community.vectorstores import SupabaseVectorStore
    from langchain_openai import OpenAIEmbeddings
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
    from langchain.callbacks.manager import CallbackManagerForRetrieverRun
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    SupabaseVectorStore = None
    OpenAIEmbeddings = None
    Document = None
    BaseRetriever = None

from ..database.supabase import get_supabase_client


class LangChainVectorStorage:
    """
    LangChain-based vector storage service
    Provides automatic LangSmith tracing via LangChain's built-in components
    """
    
    def __init__(self):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain packages not installed. Install: langchain, langchain-community, langchain-openai")
        
        self.supabase = get_supabase_client()
        if not self.supabase:
            raise ValueError("Supabase client not available")
        
        # Initialize OpenAI embeddings (automatically traced by LangSmith)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize vector stores for each table
        # Note: LangChain's SupabaseVectorStore expects specific table structure
        # We'll create custom retrievers that work with our existing schema
    
    def _create_message_vector_store(self, user_id: UUID, project_id: Optional[UUID] = None) -> Optional[SupabaseVectorStore]:
        """
        Create a vector store for message embeddings
        Uses a custom query to filter by user_id and project_id
        """
        try:
            # LangChain's SupabaseVectorStore expects:
            # - table_name: name of the table
            # - embedding_column: name of the embedding column
            # - text_column: name of the text column
            # - metadata_columns: list of metadata column names
            
            # For message_embeddings table
            vector_store = SupabaseVectorStore(
                client=self.supabase,
                embedding=self.embeddings,
                table_name="message_embeddings",
                query_name="match_message_embeddings",  # Custom RPC function
            )
            return vector_store
        except Exception as e:
            print(f"ERROR: Failed to create message vector store: {e}")
            return None
    
    def _create_document_vector_store(self, user_id: UUID, project_id: Optional[UUID] = None) -> Optional[SupabaseVectorStore]:
        """
        Create a vector store for document embeddings
        """
        try:
            vector_store = SupabaseVectorStore(
                client=self.supabase,
                embedding=self.embeddings,
                table_name="document_embeddings",
                query_name="match_document_embeddings",  # Custom RPC function
            )
            return vector_store
        except Exception as e:
            print(f"ERROR: Failed to create document vector store: {e}")
            return None
    
    def _create_global_knowledge_vector_store(self) -> Optional[SupabaseVectorStore]:
        """
        Create a vector store for global knowledge
        """
        try:
            vector_store = SupabaseVectorStore(
                client=self.supabase,
                embedding=self.embeddings,
                table_name="global_knowledge",
                query_name="match_global_knowledge",  # Custom RPC function
            )
            return vector_store
        except Exception as e:
            print(f"ERROR: Failed to create global knowledge vector store: {e}")
            return None
    
    def get_message_retriever(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        k: int = 10,
        score_threshold: float = 0.7
    ) -> Optional[BaseRetriever]:
        """
        Get a LangChain retriever for user messages
        This will automatically trace in LangSmith when LANGSMITH_TRACING=true
        """
        vector_store = self._create_message_vector_store(user_id, project_id)
        if not vector_store:
            return None
        
        # Create retriever with filters
        retriever = vector_store.as_retriever(
            search_kwargs={
                "k": k,
                "score_threshold": score_threshold,
                "filter": {
                    "user_id": str(user_id),
                    "project_id": str(project_id) if project_id else None
                }
            }
        )
        return retriever
    
    def get_document_retriever(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        k: int = 5,
        score_threshold: float = 0.7
    ) -> Optional[BaseRetriever]:
        """
        Get a LangChain retriever for documents
        This will automatically trace in LangSmith when LANGSMITH_TRACING=true
        """
        vector_store = self._create_document_vector_store(user_id, project_id)
        if not vector_store:
            return None
        
        retriever = vector_store.as_retriever(
            search_kwargs={
                "k": k,
                "score_threshold": score_threshold,
                "filter": {
                    "user_id": str(user_id),
                    "project_id": str(project_id) if project_id else None
                }
            }
        )
        return retriever
    
    def get_global_knowledge_retriever(
        self,
        k: int = 5,
        score_threshold: float = 0.7
    ) -> Optional[BaseRetriever]:
        """
        Get a LangChain retriever for global knowledge
        This will automatically trace in LangSmith when LANGSMITH_TRACING=true
        """
        vector_store = self._create_global_knowledge_vector_store()
        if not vector_store:
            return None
        
        retriever = vector_store.as_retriever(
            search_kwargs={
                "k": k,
                "score_threshold": score_threshold
            }
        )
        return retriever
    
    async def add_message(
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
        Add a message to the vector store
        """
        try:
            vector_store = self._create_message_vector_store(user_id, project_id)
            if not vector_store:
                return False
            
            # Create document
            doc = Document(
                page_content=content[:500],  # Truncate for snippet
                metadata={
                    "message_id": str(message_id),
                    "user_id": str(user_id),
                    "project_id": str(project_id),
                    "session_id": str(session_id),
                    "role": role,
                    **(metadata or {})
                }
            )
            
            # Add to vector store (this will generate embedding and store)
            vector_store.add_documents([doc])
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to add message: {e}")
            return False
    
    async def add_document_chunk(
        self,
        asset_id: UUID,
        user_id: UUID,
        project_id: Optional[UUID],
        document_type: str,
        chunk_index: int,
        chunk_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a document chunk to the vector store
        """
        try:
            vector_store = self._create_document_vector_store(user_id, project_id)
            if not vector_store:
                return False
            
            doc = Document(
                page_content=chunk_text,
                metadata={
                    "asset_id": str(asset_id),
                    "user_id": str(user_id),
                    "project_id": str(project_id) if project_id else None,
                    "document_type": document_type,
                    "chunk_index": chunk_index,
                    **(metadata or {})
                }
            )
            
            vector_store.add_documents([doc])
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to add document chunk: {e}")
            return False


# Global singleton instance
_langchain_vector_storage = None

def get_langchain_vector_storage():
    """Get or create the LangChain vector storage singleton"""
    global _langchain_vector_storage
    if _langchain_vector_storage is None:
        if LANGCHAIN_AVAILABLE:
            _langchain_vector_storage = LangChainVectorStorage()
        else:
            raise ImportError("LangChain not available")
    return _langchain_vector_storage

