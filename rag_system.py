import os
import chromadb
import requests
from groq import Groq
from typing import List, Dict, Any
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeTranscriptRAG:
    def __init__(self, chroma_db_path="./chroma_db", embedding_model="nomic-embed-text"):
        """
        Initialize the RAG system for YouTube transcripts
        
        Args:
            chroma_db_path: Path to ChromaDB
            embedding_model: Ollama embedding model to use
        """
        self.chroma_db_path = chroma_db_path
        self.embedding_model = embedding_model
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_db_path)
        self.collection = self.client.get_collection(name="youtube_transcripts")
        
        # Initialize Groq client
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        logger.info("RAG system initialized successfully")
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """
        Get embedding for the user query
        
        Args:
            query: User query string
            
        Returns:
            Query embedding as list of floats
        """
        try:
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": query
                }
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Error getting query embedding: {e}")
            raise
    
    def retrieve_relevant_chunks(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Retrieve relevant transcript chunks for the query
        
        Args:
            query: User query
            n_results: Number of results to retrieve
            
        Returns:
            Dictionary containing retrieved documents and metadata
        """
        try:
            # Get query embedding
            query_embedding = self._get_query_embedding(query)
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving relevant chunks: {e}")
            raise
    
    def format_context(self, retrieval_results: Dict[str, Any]) -> str:
        """
        Format retrieved chunks into context for the LLM
        
        Args:
            retrieval_results: Results from ChromaDB query
            
        Returns:
            Formatted context string
        """
        try:
            documents = retrieval_results["documents"][0]
            metadatas = retrieval_results["metadatas"][0]
            
            context_parts = []
            
            for doc, metadata in zip(documents, metadatas):
                video_title = metadata.get("video_title", "Unknown Video")
                video_url = metadata.get("video_url", "")
                
                context_part = f"""
Video: {video_title}
URL: {video_url}
Content: {doc}
---
"""
                context_parts.append(context_part)
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error formatting context: {e}")
            return ""
    
    def generate_response(self, query: str, context: str) -> str:
        """
        Generate response using Groq API
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Generated response
        """
        try:
            system_prompt = """You are an AI assistant that helps answer questions based on YouTube video transcripts. 
            Use the provided context from video transcripts to answer the user's question accurately and comprehensively.
            
            Guidelines:
            1. Base your answer primarily on the provided context
            2. If the context doesn't contain enough information, acknowledge this
            3. When referencing information, mention which video it came from
            4. Provide clear, well-structured answers
            5. Include relevant video titles and URLs when helpful
            """
            
            user_prompt = f"""
            Context from YouTube videos:
            {context}
            
            Question: {query}
            
            Please provide a comprehensive answer based on the video transcripts above.
            """
            
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.1-8b-instant",  # or another available model
                temperature=0.1,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error generating response: {e}"
    
    def query(self, user_query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Complete RAG pipeline for answering queries
        
        Args:
            user_query: User's question
            n_results: Number of relevant chunks to retrieve
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            logger.info(f"Processing query: {user_query}")
            
            # Retrieve relevant chunks
            retrieval_results = self.retrieve_relevant_chunks(user_query, n_results)
            
            # Format context
            context = self.format_context(retrieval_results)
            
            # Generate response
            response = self.generate_response(user_query, context)
            
            # Prepare source information
            sources = []
            if retrieval_results["metadatas"]:
                for metadata in retrieval_results["metadatas"][0]:
                    source_info = {
                        "video_title": metadata.get("video_title", "Unknown"),
                        "video_url": metadata.get("video_url", ""),
                        "filename": metadata.get("filename", "")
                    }
                    if source_info not in sources:
                        sources.append(source_info)
            
            return {
                "response": response,
                "sources": sources,
                "context": context,
                "query": user_query
            }
            
        except Exception as e:
            logger.error(f"Error in query pipeline: {e}")
            return {
                "response": f"Error processing your query: {e}",
                "sources": [],
                "context": "",
                "query": user_query
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get information about the RAG system
        
        Returns:
            System information dictionary
        """
        try:
            doc_count = self.collection.count()
            return {
                "status": "ready",
                "document_count": doc_count,
                "embedding_model": self.embedding_model,
                "llm_model": "llama3-8b-8192"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

# Example usage and testing
def test_rag_system():
    """Test function for the RAG system"""
    try:
        # Initialize RAG system
        rag = YouTubeTranscriptRAG()
        
        # Get system info
        info = rag.get_system_info()
        print(f"System Status: {info}")
        
        # Test query
        test_query = "What is the main topic discussed in the videos?"
        result = rag.query(test_query)
        
        print(f"\nQuery: {result['query']}")
        print(f"Response: {result['response']}")
        print(f"Sources: {len(result['sources'])} videos referenced")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    test_rag_system()