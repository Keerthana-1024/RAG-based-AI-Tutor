import os
import subprocess
import json
from pathlib import Path

def download_playlist_subtitles(playlist_url, output_folder="data/raw_transcripts"):
    """
    Download subtitles for all videos in a YouTube playlist
    """
    os.makedirs(output_folder, exist_ok=True)
    
    # yt-dlp command to download auto subtitles without downloading videos
    # -o: output template, includes playlist_index for ordering
    command = [
        "yt-dlp",
        "--write-auto-sub",      # write automatic subtitles
        "--sub-lang", "en",      # language: English
        "--skip-download",       # don't download video files
        "--write-info-json",     # write video metadata
        "-o", os.path.join(output_folder, "%(playlist_index)s_%(title)s.%(ext)s"),
        playlist_url
    ]
    
    print("Running yt-dlp to download subtitles...")
    try:
        subprocess.run(command, check=True)
        print(f"Subtitles downloaded to folder: {output_folder}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading subtitles: {e}")
        return False

def convert_vtt_to_txt(raw_folder="data/raw_transcripts", processed_folder="data/processed_transcripts"):
    """
    Convert VTT subtitle files to clean TXT files
    """
    os.makedirs(processed_folder, exist_ok=True)
    
    raw_path = Path(raw_folder)
    processed_path = Path(processed_folder)
    
    # Find all .vtt files
    vtt_files = list(raw_path.glob("*.vtt"))
    
    for vtt_file in vtt_files:
        print(f"Processing: {vtt_file.name}")
        
        try:
            # Read VTT file
            with open(vtt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean VTT content
            lines = content.split('\n')
            text_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip VTT headers, timestamps, and empty lines
                if (line and 
                    not line.startswith('WEBVTT') and 
                    not line.startswith('NOTE') and
                    not '-->' in line and
                    not line.isdigit() and
                    not line.startswith('<')):
                    text_lines.append(line)
            
            # Join lines and clean up
            clean_text = ' '.join(text_lines)
            # Remove multiple spaces
            clean_text = ' '.join(clean_text.split())
            
            # Get corresponding info.json for video metadata
            json_file = vtt_file.with_suffix('.info.json')
            video_title = vtt_file.stem
            video_url = ""
            
            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        video_title = metadata.get('title', video_title)
                        video_url = metadata.get('webpage_url', '')
                except:
                    pass
            
            # Create output filename
            output_filename = f"{vtt_file.stem}.txt"
            output_path = processed_path / output_filename
            
            # Write processed text with metadata
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Video Title: {video_title}\n")
                f.write(f"Video URL: {video_url}\n")
                f.write(f"{'='*50}\n\n")
                f.write(clean_text)
            
            print(f"Saved: {output_filename}")
            
        except Exception as e:
            print(f"Error processing {vtt_file.name}: {e}")
    
    print(f"Processed transcripts saved to: {processed_folder}")

def process_youtube_playlist(playlist_url):
    """
    Complete pipeline to download and process YouTube playlist transcripts
    """
    print("Starting YouTube transcript processing pipeline...")
    
    # Step 1: Download subtitles
    if download_playlist_subtitles(playlist_url):
        print("✅ Subtitles downloaded successfully")
        
        # Step 2: Convert VTT to TXT
        convert_vtt_to_txt()
        print("✅ Transcripts processed successfully")
        
        return True
    else:
        print("❌ Failed to download subtitles")
        return False

if __name__ == "__main__":
    # Replace with your target playlist URL
    playlist_url = "https://www.youtube.com/watch?v=0Jp4gsfOLMs&list=PLblh5JKOoLUJJpBNfk8_YadPwDTO2SCbx"
    
    success = process_youtube_playlist(playlist_url)
    
    if success:
        print("\n🎉 All transcripts are ready for RAG processing!")
    else:
        print("\n❌ Pipeline failed. Please check the errors above.")