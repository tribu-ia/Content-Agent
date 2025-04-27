import os
import google.generativeai as genai
from pathlib import Path
import json
from typing import Dict, Optional
from decouple import config
import time

# Configure the API key from .env file
GEMINI_API_KEY = config('GEMINI_API_KEY', default=None)
if not GEMINI_API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY in your .env file")

# Configure the API
genai.configure(api_key=GEMINI_API_KEY)

def analyze_video_for_social_media(video_path: str) -> Optional[Dict]:
    """
    Analyzes a video to find engaging moments suitable for social media.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Dictionary containing analysis results
    """
    try:
        # 1. Upload the video file
        print(f"Uploading video file: {video_path}...")
        video_file = genai.upload_file(path=video_path)
        print(f"Completed upload: {video_file.uri}")

        # 2. Wait for file processing
        print("Waiting for file processing...", end='')
        while True:
            try:
                file_status = genai.get_file(video_file.name)
                if file_status.state == "ACTIVE":
                    print('\nFile is ready for analysis!')
                    break
                elif file_status.state == "FAILED":
                    raise ValueError(f"File processing failed: {file_status.state}")
                print('.', end='', flush=True)
                time.sleep(1)
            except Exception as e:
                print(f'\nError checking file status: {e}')
                return None

        # 3. Generate content with the video
        prompt = """
        Analyze this video and identify the most engaging moments that would work well for Instagram and TikTok posts.
        For each moment, provide:
        1. Timestamp (HH:MM:SS)
        2. Brief description of the moment
        3. Why it would be engaging for social media
        4. Suggested caption/hook
        5. Whether it's better suited for Instagram or TikTok

        Focus on moments that are:
        - Visually striking
        - Emotionally engaging
        - Educational or informative
        - Humorous or surprising
        - Under 60 seconds in length

        Format your response as a JSON object with the following structure:
        {
            "moments": [
                {
                    "timestamp": "HH:MM:SS",
                    "description": "string",
                    "engagement_reason": "string",
                    "suggested_caption": "string",
                    "best_platform": "instagram|tiktok|both"
                }
            ]
        }
        """

        print("Generating analysis...")
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content([prompt, video_file])

        # 4. Parse and return the response
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            print("Error parsing response as JSON. Raw response:")
            print(response.text)
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        # Clean up: Delete the uploaded file
        if 'video_file' in locals():
            try:
                genai.delete_file(video_file.name)
                print("Uploaded file deleted successfully.")
            except Exception as e:
                print(f"Warning: Failed to delete uploaded file. Error: {e}")

def main():
    # Get the first video chunk
    chunks_dir = Path("chunks")
    video_files = list(chunks_dir.glob("*.mp4"))
    
    if not video_files:
        print("No video files found in the chunks directory")
        return
    
    # Use the first video chunk
    video_path = str(video_files[0])
    print(f"Analyzing video: {video_path}")
    
    # Analyze the video
    results = analyze_video_for_social_media(video_path)
    
    if results:
        print("\nAnalysis Results:")
        for moment in results.get("moments", []):
            print(f"\nTimestamp: {moment.get('timestamp', 'N/A')}")
            print(f"Description: {moment.get('description', 'N/A')}")
            print(f"Engagement Reason: {moment.get('engagement_reason', 'N/A')}")
            print(f"Suggested Caption: {moment.get('suggested_caption', 'N/A')}")
            print(f"Best Platform: {moment.get('best_platform', 'N/A')}")
            print("-" * 50)

if __name__ == "__main__":
    main() 