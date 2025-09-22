import streamlit as st
import requests
import json
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="YouTube Transcript RAG Chatbot",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = "http://localhost:8000"

class YouTubeRAGInterface:
    def __init__(self):
        self.api_base = API_BASE_URL
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check if the backend system is healthy"""
        try:
            response = requests.get(f"{self.api_base}/system-info", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": str(e)}
    
    def get_available_videos(self) -> Dict[str, Any]:
        """Get list of available videos"""
        try:
            response = requests.get(f"{self.api_base}/videos", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"videos": [], "error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"videos": [], "error": str(e)}
    
    def query_system(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Query the RAG system"""
        try:
            payload = {
                "query": query,
                "n_results": n_results
            }
            response = requests.post(
                f"{self.api_base}/query",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "response": f"Error: HTTP {response.status_code}",
                    "sources": [],
                    "query": query,
                    "status": "error"
                }
        except requests.exceptions.RequestException as e:
            return {
                "response": f"Error: {str(e)}",
                "sources": [],
                "query": query,
                "status": "error"
            }
    
    def search_similar_content(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Search for similar content"""
        try:
            payload = {
                "query": query,
                "n_results": n_results
            }
            response = requests.post(
                f"{self.api_base}/search",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"query": query, "results": [], "error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"query": query, "results": [], "error": str(e)}

def main():
    """Main Streamlit application"""
    
    # Initialize interface
    if 'interface' not in st.session_state:
        st.session_state.interface = YouTubeRAGInterface()
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Header
    st.title("🎥 YouTube Transcript RAG Chatbot")
    st.markdown("Ask questions about the content from YouTube video transcripts")
    
    # Sidebar
    with st.sidebar:
        st.header("System Status")
        
        # Check system health
        with st.spinner("Checking system health..."):
            health_info = st.session_state.interface.check_system_health()
        
        if health_info["status"] == "ready":
            st.success("✅ System Ready")
            st.info(f"Documents: {health_info.get('document_count', 'Unknown')}")
            st.info(f"Embedding Model: {health_info.get('embedding_model', 'Unknown')}")
            st.info(f"LLM Model: {health_info.get('llm_model', 'Unknown')}")
        else:
            st.error(f"❌ System Error: {health_info.get('error', 'Unknown error')}")
            st.warning("Please ensure the FastAPI backend is running on port 8000")
        
        st.divider()
        
        # Available Videos
        st.header("Available Videos")
        if st.button("🔄 Refresh Videos"):
            with st.spinner("Loading videos..."):
                video_info = st.session_state.interface.get_available_videos()
            
            if "error" in video_info:
                st.error(f"Error loading videos: {video_info['error']}")
            else:
                st.success(f"Found {video_info['total_count']} videos")
                
                # Display videos
                for video in video_info["videos"][:5]:  # Show first 5
                    with st.expander(f"📹 {video['title'][:50]}..."):
                        st.write(f"**Title:** {video['title']}")
                        if video['url']:
                            st.write(f"**URL:** [Link]({video['url']})")
                        st.write(f"**File:** {video['filename']}")
                
                if video_info['total_count'] > 5:
                    st.info(f"... and {video_info['total_count'] - 5} more videos")
        
        st.divider()
        
        # Settings
        st.header("Query Settings")
        n_results = st.slider(
            "Number of results to retrieve",
            min_value=1,
            max_value=10,
            value=5,
            help="How many relevant chunks to retrieve for context"
        )
        
        # Clear chat history
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.success("Chat history cleared!")
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("💬 Chat with Your Videos")
        
        # Display chat history
        for i, chat in enumerate(st.session_state.chat_history):
            with st.chat_message("user"):
                st.write(chat["query"])
            
            with st.chat_message("assistant"):
                st.write(chat["response"])
                
                # Show sources if available
                if chat.get("sources"):
                    with st.expander("📚 Sources"):
                        for j, source in enumerate(chat["sources"], 1):
                            st.write(f"**{j}. {source['video_title']}**")
                            if source['video_url']:
                                st.write(f"   🔗 [Watch Video]({source['video_url']})")
        
        # Query input
        user_query = st.chat_input("Ask a question about the videos...")
        
        if user_query:
            # Add user message to chat
            with st.chat_message("user"):
                st.write(user_query)
            
            # Get response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    result = st.session_state.interface.query_system(user_query, n_results)
                
                st.write(result["response"])
                
                # Show sources
                if result.get("sources"):
                    with st.expander("📚 Sources"):
                        for i, source in enumerate(result["sources"], 1):
                            st.write(f"**{i}. {source['video_title']}**")
                            if source['video_url']:
                                st.write(f"   🔗 [Watch Video]({source['video_url']})")
                
                # Add to chat history
                st.session_state.chat_history.append(result)
    
    with col2:
        st.header("🔍 Content Search")
        st.markdown("Search for similar content without generating a response")
        
        # Search functionality
        search_query = st.text_input(
            "Search query:",
            placeholder="Enter keywords to search...",
            key="search_input"
        )
        
        search_n_results = st.selectbox(
            "Results to show:",
            options=[3, 5, 7, 10],
            index=1,
            key="search_results"
        )
        
        if st.button("🔍 Search", key="search_button"):
            if search_query:
                with st.spinner("Searching..."):
                    search_results = st.session_state.interface.search_similar_content(
                        search_query, search_n_results
                    )
                
                if "error" in search_results:
                    st.error(f"Search error: {search_results['error']}")
                else:
                    st.success(f"Found {search_results['total_results']} relevant chunks")
                    
                    for i, result in enumerate(search_results["results"], 1):
                        with st.expander(f"Result {i}: {result['video_title'][:40]}..."):
                            st.write(f"**Video:** {result['video_title']}")
                            if result['video_url']:
                                st.write(f"**URL:** [Link]({result['video_url']})")
                            st.write(f"**Similarity:** {result['similarity_score']:.3f}")
                            st.write(f"**Content:**")
                            st.write(result['content'])
            else:
                st.warning("Please enter a search query")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>YouTube Transcript RAG Chatbot | Powered by Ollama, ChromaDB, and Groq</p>
        <p>💡 Tip: Ask specific questions about the video content for best results</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()