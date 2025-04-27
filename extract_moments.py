import google.generativeai as genai
import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Literal

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables or .env file.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-pro"  # Using pro model for better video analysis

# Define Pydantic models for structured output
class SocialMediaMoment(BaseModel):
    start_timestamp: str
    end_timestamp: str
    description: str
    engagement_reason: str
    suggested_caption: str
    best_platform: Literal["instagram", "tiktok", "both"]
    duration_seconds: int  # Will be calculated from timestamps

class VideoAnalysis(BaseModel):
    moments: List[SocialMediaMoment]

# --------------------

def upload_video(video_path: Path):
    """Uploads the video file to the Gemini File API."""
    print(f"Uploading video: {video_path.name}...")
    try:
        video_file = genai.upload_file(path=video_path, display_name=video_path.name)
        print(f"Video uploaded successfully. File URI: {video_file.uri}")

        # Wait for the video processing to complete
        while video_file.state.name == "PROCESSING":
            print("Waiting for video processing...", end='\r')
            time.sleep(5)  # Check every 5 seconds
            video_file = genai.get_file(video_file.name) # Refresh file state

        if video_file.state.name == "FAILED":
            print(f"\nError: Video processing failed for {video_path.name}")
            return None
        elif video_file.state.name == "ACTIVE":
            print(f"\nVideo processing complete for {video_path.name}. Ready for use.")
            return video_file
        else:
            print(f"\nUnexpected video state: {video_file.state.name}")
            return None

    except Exception as e:
        print(f"\nError uploading or processing video {video_path.name}: {e}")
        return None

def extract_key_moments(video_file):
    """Asks Gemini to extract key moments from the processed video."""
    if not video_file:
        return "Error: Invalid video file provided for extraction."

    print(f"\nAsking Gemini ({MODEL_NAME}) to extract key moments...")
    try:
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        prompt = """
        Analyze this video and identify the most engaging moments that would work well for Instagram and TikTok posts.

        IMPORTANT: Respond ONLY with a raw JSON object, no additional text, no markdown formatting.

        The JSON must follow this exact structure:
        {
            "moments": [
                {
                    "start_timestamp": "HH:MM:SS",
                    "end_timestamp": "HH:MM:SS",
                    "description": "string",
                    "engagement_reason": "string",
                    "suggested_caption": "string",
                    "best_platform": "instagram|tiktok|both",
                    "duration_seconds": number
                }
            ]
        }

        For each moment:
        - Each clip MUST be between  and 90 seconds long
        - Include both start and end timestamps
        - Calculate and include the duration in seconds
        - Focus on complete, self-contained segments
        - Ensure the clip makes sense when viewed independently

        Consider these types of engaging content:
        - Visually striking scenes
        - Emotionally engaging content
        - Educational or informative segments
        - Humorous or surprising moments
        - Clear beginnings and endings

        Remember: Return ONLY the JSON object, no other text.
        
        besides all this, please describe in detail what is displayed in the screen in the second 60 of this video
        """

        # Generate content with structured output
        response = model.generate_content(
            [prompt, video_file],
            request_options={"timeout": 600}  # Increase timeout for video
        )

        # Parse the response into our Pydantic model
        try:
            # Clean up the response text
            text = response.text
            # Remove markdown code block markers if present
            text = text.replace('```json', '').replace('```', '').strip()
            
            # First try to parse as JSON
            response_json = json.loads(text)
            # Then validate against our Pydantic model
            analysis = VideoAnalysis.model_validate(response_json)
            return analysis
        except Exception as e:
            print(f"Error parsing response: {e}")
            print("Raw response:")
            print(response.text)
            return None

    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return None

def delete_uploaded_file(video_file):
    """Deletes the file from the Gemini File API after processing."""
    if not video_file:
        return
    try:
        print(f"\nDeleting uploaded file: {video_file.name}...")
        genai.delete_file(video_file.name)
        print("File deleted successfully.")
    except Exception as e:
        print(f"Error deleting file {video_file.name}: {e}")
        print("You may need to delete it manually via the API or Google AI Studio.")

# --- Main Execution ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_moments.py <path_to_video_file>")
        sys.exit(1)

    video_path_str = sys.argv[1]
    video_path = Path(video_path_str)

    if not video_path.is_file():
        print(f"Error: Video file not found at '{video_path_str}'")
        sys.exit(1)

    uploaded_video = None
    try:
        # 1. Upload Video
        uploaded_video = upload_video(video_path)

        if uploaded_video:
            # 2. Extract Moments
            analysis = extract_key_moments(uploaded_video)

            # 3. Print Results
            if analysis:
                print("\n--- Key Moments Extracted ---")
                for moment in analysis.moments:
                    print(f"\nClip: {moment.start_timestamp} - {moment.end_timestamp} ({moment.duration_seconds}s)")
                    print(f"Description: {moment.description}")
                    print(f"Engagement Reason: {moment.engagement_reason}")
                    print(f"Suggested Caption: {moment.suggested_caption}")
                    print(f"Best Platform: {moment.best_platform}")
                    print("-" * 50)
            else:
                print("\nNo moments were extracted from the video.")

    finally:
        # 4. Clean up uploaded file (always try to delete)
        if uploaded_video:
            delete_uploaded_file(uploaded_video)

    print("\nScript finished.")
# -------------------- 