# Standard library imports
import logging
import os
import re
from pathlib import Path

# Third party imports
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# Local application imports

def extract_video_id(yt_vid_url):
    # Updated regex pattern to match various YouTube URL formats
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})(?:\S+)?'

    # Extract and return the video ID
    match = re.search(pattern, yt_vid_url)
    if match:
        return match.group(1)
    else:
        return None

def yt_vid_url_to_mp4(yt_vid_url, mp4_dir_save_path):
    # Create the directory if it doesn't exist
    os.makedirs(mp4_dir_save_path, exist_ok=True)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(mp4_dir_save_path, '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        # Additional options to bypass bot protection
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'quiet': False,
        'verbose': True,
        'cookiefile': 'cookies.txt',  # Optional: Add cookies if you have them
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'referer': 'https://www.youtube.com/',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(yt_vid_url, download=False)
            filename = ydl.prepare_filename(info)
            logging.info(f"Downloading video: {info.get('title', 'Unknown title')}")
            logging.info(f"Video duration: {info.get('duration', 'Unknown')} seconds")
            ydl.download([yt_vid_url])
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        # Let's try a simpler format as fallback
        ydl_opts_simple = {
            'format': 'best',
            'outtmpl': os.path.join(mp4_dir_save_path, '%(title)s.%(ext)s'),
            'restrictfilenames': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts_simple) as ydl:
                info = ydl.extract_info(yt_vid_url, download=True)
                filename = ydl.prepare_filename(info)
        except Exception as e2:
            logging.error(f"Second attempt to download failed: {e2}")
            raise e2

    video_file = Path(filename)

    # Ensure the file has a .mp4 extension
    if not video_file.suffix == '.mp4':
        new_video_file = video_file.with_suffix('.mp4')
        video_file.rename(new_video_file)
        video_file = new_video_file

    return str(video_file)

def yt_vid_id_to_srt(transcript, yt_video_id, srt_save_path):

    srt_content = []
    for i, entry in enumerate(transcript):
        start = entry['start']
        duration = entry['duration']
        text = entry['text']

        start_hours, start_remainder = divmod(start, 3600)
        start_minutes, start_seconds = divmod(start_remainder, 60)
        start_milliseconds = int((start_seconds - int(start_seconds)) * 1000)

        end = start + duration
        end_hours, end_remainder = divmod(end, 3600)
        end_minutes, end_seconds = divmod(end_remainder, 60)
        end_milliseconds = int((end_seconds - int(end_seconds)) * 1000)

        srt_content.append(f"{i + 1}")
        srt_content.append(
            f"{int(start_hours):02}:{int(start_minutes):02}:{int(start_seconds):02},{start_milliseconds:03} --> {int(end_hours):02}:{int(end_minutes):02}:{int(end_seconds):02},{end_milliseconds:03}")
        srt_content.append(text)
        srt_content.append('')

    # Ensure the output directory exists
    os.makedirs(srt_save_path, exist_ok=True)

    with open(os.path.join(srt_save_path, 'subtitles.srt'), 'w', encoding='utf-8') as file:
        file.write('\n'.join(srt_content))


def yt_vid_id_to_txt(transcript, yt_video_id, txt_save_path):
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(txt_save_path), exist_ok=True)

    # Write the transcript to a .txt file as a single line
    with open(os.path.join(txt_save_path, 'transcript.txt'), 'w', encoding='utf-8') as f:
        full_transcript = ' '.join(entry['text'] for entry in transcript)
        f.write(full_transcript)


def main(yt_vid_url, mp4_dir_save_path, srt_dir_save_path, txt_dir_save_path, use_chunker=True):
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    yt_video_id = extract_video_id(yt_vid_url)
    logging.info(f"Processing YouTube video ID: {yt_video_id}")

    # Try to get Spanish transcript if English is not available
    try:
        transcript = YouTubeTranscriptApi.get_transcript(yt_video_id)
        logging.info("Successfully retrieved English transcript")
    except Exception as e:
        logging.info("English transcript not available, trying Spanish transcript")
        try:
            transcript = YouTubeTranscriptApi.get_transcript(yt_video_id, languages=['es'])
            logging.info("Successfully retrieved Spanish transcript")
        except Exception as es_error:
            logging.error(f"Failed to retrieve transcript: {es_error}")
            raise es_error

    # Download the video
    video_path = yt_vid_url_to_mp4(yt_vid_url, mp4_dir_save_path)
    logging.info(f"Video downloaded to: {video_path}")
    
    # Process with chunker if needed for long videos
    if use_chunker:
        try:
            from chunker import VideoChunker
            chunker = VideoChunker()
            chunker.setup()
            
            if chunker.needs_chunking(video_path):
                logging.info("Video is long, splitting into chunks...")
                chunks = chunker.split_video(video_path)
                if chunks:
                    logging.info(f"Video split into {len(chunks)} chunks")
                else:
                    logging.warning("Failed to split video, proceeding with full video")
            else:
                logging.info("Video is short enough, no chunking needed")
        except ImportError:
            logging.warning("Chunker module not available, proceeding with full video")
    
    # Generate subtitles and transcript
    yt_vid_id_to_srt(transcript, yt_video_id, srt_dir_save_path)
    yt_vid_id_to_txt(transcript, yt_video_id, txt_dir_save_path)
    
    logging.info("Processing complete!")
    return video_path

if __name__ == "__main__":
    yt_vid_url = input("Enter the YouTube URL: ")
    yt_video_id = extract_video_id(yt_vid_url)
    mp4_dir_save_path = "./input_files"
    srt_dir_save_path = "./whisper_output"
    txt_dir_save_path = "./whisper_output"
    main(yt_vid_url, mp4_dir_save_path, srt_dir_save_path, txt_dir_save_path)