#!/usr/bin/env python3
"""
Complete setup script for YouTube Transcript RAG System
This script handles the entire pipeline from downloading transcripts to running the RAG system.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouTubeRAGSetup:
    def __init__(self):
        self.project_root = Path.cwd()
        self.data_dir = self.project_root / "data"
        self.raw_transcripts_dir = self.data_dir / "raw_transcripts"
        self.processed_transcripts_dir = self.data_dir / "processed_transcripts"
        self.chroma_db_path = self.project_root / "chroma_db"
    
    def create_directories(self):
        """Create necessary directories"""
        logger.info("Creating project directories...")
        
        directories = [
            self.data_dir,
            self.raw_transcripts_dir,
            self.processed_transcripts_dir,
            self.chroma_db_path
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created directory: {directory}")
        return True
        
    
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        logger.info("Checking dependencies...")
        
        dependencies = {
            "yt-dlp": "yt-dlp --version",
            "ollama": "ollama --version"
        }
        
        missing_deps = []
        for dep, cmd in dependencies.items():
            try:
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"✅ {dep} is installed")
                else:
                    missing_deps.append(dep)
            except FileNotFoundError:
                missing_deps.append(dep)
        
        if missing_deps:
            logger.error(f"❌ Missing dependencies: {', '.join(missing_deps)}")
            logger.info("Please install missing dependencies:")
            for dep in missing_deps:
                if dep == "yt-dlp":
                    logger.info("  pip install yt-dlp")
                elif dep == "ollama":
                    logger.info("  Visit https://ollama.ai for installation instructions")
            return False
        
        return True
    
    def setup_ollama_model(self):
        """Download and setup Ollama embedding model"""
        logger.info("Setting up Ollama embedding model...")
        
        try:
            # Check if Ollama is running
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("❌ Ollama is not running. Please start Ollama first.")
                return False
            
            # Pull the embedding model
            logger.info("Pulling nomic-embed-text model...")
            result = subprocess.run(["ollama", "pull", "nomic-embed-text"], check=True)
            logger.info("✅ Ollama model setup complete")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error setting up Ollama model: {e}")
            return False
    
    def install_python_dependencies(self):
        """Install Python dependencies"""
        logger.info("Installing Python dependencies...")
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            logger.info("✅ Python dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error installing dependencies: {e}")
            return False
    
    def download_transcripts(self, playlist_url):
        """Download YouTube transcripts"""
        logger.info(f"Downloading transcripts from playlist: {playlist_url}")
        
        try:
            from youtube_downloader import process_youtube_playlist
            success = process_youtube_playlist(playlist_url)
            if success:
                logger.info("✅ Transcripts downloaded and processed")
                return True
            else:
                logger.error("❌ Failed to download transcripts")
                return False
        except ImportError as e:
            logger.error(f"❌ Error importing youtube_downloader: {e}")
            return False
    
    def ingest_data(self):
        """Run data ingestion pipeline"""
        logger.info("Starting data ingestion...")
        
        try:
            from data_ingestion import TranscriptIngestion
            ingestion = TranscriptIngestion()
            success = ingestion.ingest_transcripts()
            if success:
                logger.info("✅ Data ingestion completed")
                return True
            else:
                logger.error("❌ Data ingestion failed")
                return False
        except ImportError as e:
            logger.error(f"❌ Error importing data_ingestion: {e}")
            return False
    
    def create_env_file(self):
        """Create .env file if it doesn't exist"""
        env_file = self.project_root / ".env"
        
        if not env_file.exists():
            logger.info("Creating .env file...")
            
            groq_key = input("Enter your Groq API key (or press Enter to skip): ").strip()
            
            env_content = f"""# Groq API Configuration
                                GROQ_API_KEY={groq_key}

                                # Ollama Configuration
                                OLLAMA_BASE_URL=http://localhost:11434
                                EMBEDDING_MODEL=nomic-embed-text

                                # ChromaDB Configuration
                                CHROMA_DB_PATH=./chroma_db

                                # API Configuration
                                API_HOST=0.0.0.0
                                API_PORT=8000

                                # Streamlit Configuration
                                STREAMLIT_PORT=8501
                                """
            
            with open(env_file, 'w') as f:
                f.write(env_content)
            
            logger.info("✅ .env file created")
        else:
            logger.info("✅ .env file already exists")
        return True
    
    def run_complete_setup(self, playlist_url=None):
        """Run the complete setup pipeline"""
        logger.info("🚀 Starting YouTube RAG System Setup")
        
        steps = [
            ("Creating directories", self.create_directories),
            ("Checking dependencies", self.check_dependencies),
            ("Installing Python dependencies", self.install_python_dependencies),
            ("Setting up Ollama model", self.setup_ollama_model),
            ("Creating environment file", self.create_env_file),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Step: {step_name}")
            if not step_func():
                logger.error(f"❌ Setup failed at step: {step_name}")
                return False
        
        # Download transcripts if playlist URL provided
        if playlist_url:
            logger.info("Step: Downloading transcripts")
            if not self.download_transcripts(playlist_url):
                logger.error("❌ Setup failed at transcript download")
                return False
            
            logger.info("Step: Ingesting data")
            if not self.ingest_data():
                logger.error("❌ Setup failed at data ingestion")
                return False
        
        logger.info("🎉 Setup completed successfully!")
        logger.info("\nNext steps:")
        if playlist_url:
            logger.info("1. Start the FastAPI backend: uvicorn main:app --reload")
            logger.info("2. Start the Streamlit frontend: streamlit run streamlit_app.py")
        else:
            logger.info("1. Run: python youtube_downloader.py (with your playlist URL)")
            logger.info("2. Run: python data_ingestion.py")
            logger.info("3. Start the FastAPI backend: uvicorn main:app --reload")
            logger.info("4. Start the Streamlit frontend: streamlit run streamlit_app.py")
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Setup YouTube Transcript RAG System")
    parser.add_argument(
        "--playlist-url", 
        type=str, 
        help="YouTube playlist URL to download transcripts from"
    )
    parser.add_argument(
        "--skip-transcripts", 
        action="store_true", 
        help="Skip transcript download and ingestion"
    )
    
    args = parser.parse_args()
    
    setup = YouTubeRAGSetup()
    
    playlist_url = args.playlist_url
    if not args.skip_transcripts and not playlist_url:
        playlist_url = input("Enter YouTube playlist URL (or press Enter to skip): ").strip()
        if not playlist_url:
            playlist_url = None
    
    success = setup.run_complete_setup(playlist_url)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()