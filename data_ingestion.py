import os
import glob
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import requests
from typing import List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptIngestion:
    def __init__(self, chroma_db_path="./chroma_db", embedding_model="nomic-embed-text"):
        """
        Initialize the transcript ingestion system
        
        Args:
            chroma_db_path: Path to store ChromaDB
            embedding_model: Ollama embedding model to use
        """
        self.chroma_db_path = chroma_db_path
        self.embedding_model = embedding_model
        self.client = None
        self.collection = None
        
        # Initialize ChromaDB
        self._initialize_chromadb()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection"""
        try:
            self.client = chromadb.PersistentClient(path=self.chroma_db_path)
            self.collection = self.client.get_or_create_collection(
                name="youtube_transcripts",
                metadata={"description": "YouTube video transcripts for RAG"}
            )
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise
    
    def _get_ollama_embedding(self, text: str) -> List[float]:
        """
        Get embedding from Ollama API
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        try:
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def load_transcripts(self, transcript_folder="data/processed_transcripts") -> List[Document]:
        """
        Load all transcript files from the processed folder
        
        Args:
            transcript_folder: Path to the processed transcripts folder
            
        Returns:
            List of Document objects
        """
        documents = []
        transcript_files = glob.glob(os.path.join(transcript_folder, "*.txt"))
        
        if not transcript_files:
            logger.warning(f"No transcript files found in {transcript_folder}")
            return documents
        
        for file_path in transcript_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract metadata from the content
                lines = content.split('\n')
                video_title = ""
                video_url = ""
                transcript_text = content
                
                # Parse metadata if present
                if len(lines) > 0 and lines[0].startswith("Video Title:"):
                    video_title = lines[0].replace("Video Title:", "").strip()
                if len(lines) > 1 and lines[1].startswith("Video URL:"):
                    video_url = lines[1].replace("Video URL:", "").strip()
                if len(lines) > 3:
                    transcript_text = '\n'.join(lines[3:])  # Skip metadata lines
                
                # Create document
                doc = Document(
                    page_content=transcript_text,
                    metadata={
                        "source": file_path,
                        "video_title": video_title,
                        "video_url": video_url,
                        "filename": os.path.basename(file_path)
                    }
                )
                documents.append(doc)
                logger.info(f"Loaded transcript: {video_title}")
                
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        logger.info(f"Loaded {len(documents)} transcript documents")
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into smaller chunks
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of split Document objects
        """
        try:
            split_docs = self.text_splitter.split_documents(documents)
            logger.info(f"Split {len(documents)} documents into {len(split_docs)} chunks")
            return split_docs
        except Exception as e:
            logger.error(f"Error splitting documents: {e}")
            raise
    
    def add_to_chromadb(self, documents: List[Document]):
        """
        Add documents to ChromaDB with embeddings
        
        Args:
            documents: List of Document objects to add
        """
        try:
            # Clear existing collection
            # self.collection.delete(where={}) # causes issues 
            # Instead of collection.delete(where={})
            # Clear all docs safely
            all_ids = self.collection.get()["ids"]
            if all_ids:
                self.collection.delete(ids=all_ids)


            logger.info("Cleared existing collection")
            
            texts = []
            metadatas = []
            ids = []
            embeddings = []
            
            for i, doc in enumerate(documents):
                # Generate embedding
                embedding = self._get_ollama_embedding(doc.page_content)
                
                texts.append(doc.page_content)
                metadatas.append(doc.metadata)
                ids.append(f"doc_{i}")
                embeddings.append(embedding)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(documents)} documents")
            
            # Add to ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully added {len(documents)} documents to ChromaDB")
            
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {e}")
            raise
    
    def ingest_transcripts(self, transcript_folder="data/processed_transcripts"):
        """
        Complete ingestion pipeline
        
        Args:
            transcript_folder: Path to processed transcripts
        """
        try:
            logger.info("Starting transcript ingestion pipeline...")
            
            # Load transcripts
            documents = self.load_transcripts(transcript_folder)
            
            if not documents:
                logger.error("No documents loaded. Exiting.")
                return False
            
            # Split documents
            split_docs = self.split_documents(documents)
            
            # Add to ChromaDB
            self.add_to_chromadb(split_docs)
            
            logger.info("✅ Transcript ingestion completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ingestion pipeline failed: {e}")
            return False
    
    def get_collection_info(self):
        """Get information about the current collection"""
        try:
            count = self.collection.count()
            logger.info(f"Collection contains {count} documents")
            return count
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return 0

def main():
    """Main function to run the ingestion pipeline"""
    ingestion = TranscriptIngestion()
    
    # Check if processed transcripts exist
    transcript_folder = "data/processed_transcripts"
    if not os.path.exists(transcript_folder):
        logger.error(f"Processed transcripts folder not found: {transcript_folder}")
        logger.error("Please run the YouTube downloader first to process transcripts.")
        return
    
    # Run ingestion
    success = ingestion.ingest_transcripts(transcript_folder)
    
    if success:
        info = ingestion.get_collection_info()
        print(f"\n🎉 Ingestion completed! {info} document chunks available for querying.")
    else:
        print("\n❌ Ingestion failed. Check the logs for details.")

if __name__ == "__main__":
    main()