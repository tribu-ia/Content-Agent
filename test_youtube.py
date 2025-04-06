import logging
import sys
from ytdl import main as ytdl_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_youtube_download():
    """Test downloading and processing a YouTube video."""
    # The URL you provided
    yt_vid_url = "https://www.youtube.com/watch?v=DlWOIWK1_mk&ab_channel=TribuIAColombia"
    
    # Directories for saving files
    mp4_dir_save_path = "./input_files"
    srt_dir_save_path = "./whisper_output"
    txt_dir_save_path = "./whisper_output"
    
    logging.info(f"Testing YouTube download for URL: {yt_vid_url}")
    
    try:
        video_path = ytdl_main(
            yt_vid_url, 
            mp4_dir_save_path, 
            srt_dir_save_path, 
            txt_dir_save_path,
            use_chunker=True
        )
        
        logging.info(f"Test completed successfully!")
        logging.info(f"Video saved to: {video_path}")
        return True
    except Exception as e:
        logging.error(f"Test failed with error: {e}")
        return False

if __name__ == "__main__":
    test_youtube_download() 