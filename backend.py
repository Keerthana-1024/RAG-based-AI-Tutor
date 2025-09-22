from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from rag_system import YouTubeTranscriptRAG
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="YouTube Transcript RAG API",
    description="API for querying YouTube video transcripts using RAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global RAG system instance
rag_system = None

# Pydantic models for request/response
class QueryRequest(BaseModel):
    query: str
    n_results: Optional[int] = 5

class SourceInfo(BaseModel):
    video_title: str
    video_url: str
    filename: str

class QueryResponse(BaseModel):
    response: str
    sources: List[SourceInfo]
    query: str
    status: str

class SystemInfoResponse(BaseModel):
    status: str
    document_count: Optional[int] = None
    embedding_model: Optional[str] = None
    llm_model: Optional[str] = None
    error: Optional[str] = None

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the RAG system on startup"""
    global rag_system
    try:
        logger.info("Initializing RAG system...")
        rag_system = YouTubeTranscriptRAG()
        logger.info("RAG system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        rag_system = None

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {
        "message": "YouTube Transcript RAG API is running",
        "status": "healthy" if rag_system is not None else "unhealthy"
    }

# System information endpoint
@app.get("/system-info", response_model=SystemInfoResponse)
async def get_system_info():
    """Get information about the RAG system"""
    if rag_system is None:
        return SystemInfoResponse(
            status="error",
            error="RAG system not initialized"
        )
    
    try:
        info = rag_system.get_system_info()
        return SystemInfoResponse(**info)
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Main query endpoint
@app.post("/query", response_model=QueryResponse)
async def query_transcripts(request: QueryRequest):
    """Query the YouTube transcripts using RAG"""
    if rag_system is None:
        raise HTTPException(
            status_code=503, 
            detail="RAG system not initialized. Please check server logs."
        )
    
    if not request.query.strip():
        raise HTTPException(
            status_code=400, 
            detail="Query cannot be empty"
        )
    
    try:
        logger.info(f"Processing query: {request.query}")
        
        result = rag_system.query(request.query, request.n_results)
        
        # Convert sources to SourceInfo models
        sources = [
            SourceInfo(
                video_title=source.get("video_title", "Unknown"),
                video_url=source.get("video_url", ""),
                filename=source.get("filename", "")
            )
            for source in result["sources"]
        ]
        
        return QueryResponse(
            response=result["response"],
            sources=sources,
            query=result["query"],
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to get available videos
@app.get("/videos")
async def get_available_videos():
    """Get list of available videos in the system"""
    if rag_system is None:
        raise HTTPException(
            status_code=503, 
            detail="RAG system not initialized"
        )
    
    try:
        # Get all documents from ChromaDB to extract unique videos
        results = rag_system.collection.get(include=["metadatas"])
        
        videos = {}
        for metadata in results["metadatas"]:
            video_title = metadata.get("video_title", "Unknown")
            video_url = metadata.get("video_url", "")
            filename = metadata.get("filename", "")
            
            if video_title not in videos:
                videos[video_title] = {
                    "title": video_title,
                    "url": video_url,
                    "filename": filename
                }
        
        return {
            "videos": list(videos.values()),
            "total_count": len(videos)
        }
        
    except Exception as e:
        logger.error(f"Error getting available videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint for similarity search
@app.post("/search")
async def search_similar_content(request: QueryRequest):
    """Search for similar content without generating a response"""
    if rag_system is None:
        raise HTTPException(
            status_code=503, 
            detail="RAG system not initialized"
        )
    
    if not request.query.strip():
        raise HTTPException(
            status_code=400, 
            detail="Query cannot be empty"
        )
    
    try:
        logger.info(f"Searching for: {request.query}")
        
        retrieval_results = rag_system.retrieve_relevant_chunks(
            request.query, 
            request.n_results
        )
        
        # Format results
        results = []
        if retrieval_results["documents"]:
            documents = retrieval_results["documents"][0]
            metadatas = retrieval_results["metadatas"][0]
            distances = retrieval_results["distances"][0] if retrieval_results.get("distances") else [0] * len(documents)
            
            for doc, metadata, distance in zip(documents, metadatas, distances):
                results.append({
                    "content": doc[:200] + "..." if len(doc) > 200 else doc,
                    "video_title": metadata.get("video_title", "Unknown"),
                    "video_url": metadata.get("video_url", ""),
                    "similarity_score": 1 - distance,  # Convert distance to similarity
                    "filename": metadata.get("filename", "")})
        
        return {
            "query": request.query,
            "results": results,
            "total_results": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error searching content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Run the server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )