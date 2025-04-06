#!/usr/bin/env python

# Standard library imports
import os
import warnings
import sys
import traceback
from pathlib import Path

# Third party imports
from dotenv import load_dotenv

# Local application imports
import clipper
import subtitler
import crew
from local_transcribe import local_whisper_process
import extracts
from utils import (
    setup_logging,
    create_directories,
    save_checkpoint,
    load_checkpoint,
    retry_operation,
    get_timestamp
)

# Setup logging
logger = setup_logging()

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

def clean_output_folder(folder_path):
    """Clean output folder by removing files"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return
    
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                logger.info(f"Removed {file_path}")
        except Exception as e:
            logger.error(f"Error while removing {file_path}: {e}")

def process_test_video():
    """Process a test video through the complete pipeline"""
    # Folder setup
    input_folder = './test_input'
    output_video_folder = './test_output/clipper_output'
    crew_output_folder = './crew_output'
    whisper_output_folder = './test_output/whisper_output'
    subtitler_output_folder = './test_output/subtitler_output'
    
    # Create necessary directories
    folders = [
        input_folder, output_video_folder, crew_output_folder, 
        whisper_output_folder, subtitler_output_folder
    ]
    create_directories(folders)
    
    # Clean output directories
    for folder in [output_video_folder, crew_output_folder, whisper_output_folder, subtitler_output_folder]:
        clean_output_folder(folder)
        logger.info(f"Cleaned output folder: {folder}")
    
    # Get the test video
    input_video_path = os.path.join(input_folder, 'test_5min_clip.mp4')
    if not os.path.exists(input_video_path):
        logger.error(f"Test video not found: {input_video_path}")
        return False
    
    logger.info(f"Using test video: {input_video_path}")
    
    # Set aspect ratio choice (1=original, 2=square)
    aspect_ratio_choice = '1'
    
    # STAGE 1: TRANSCRIBE - Generate transcription using Whisper
    logger.info("STAGE 1: Transcribing video")
    
    try:
        # Transcribe the video
        local_whisper_process(os.path.dirname(input_video_path), whisper_output_folder)
        logger.info("Transcription completed successfully")
    except Exception as e:
        error_msg = f"Error during transcription: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 2: EXTRACT - Generate viral extracts using GPT
    logger.info("STAGE 2: Generating viral extracts")
    
    try:
        extracts_data = retry_operation(extracts.main)
        if extracts_data is None:
            logger.error("Failed to generate extracts")
            return False
        
        logger.info(f"Generated {len(extracts_data)} extracts")
        for i, extract in enumerate(extracts_data):
            logger.info(f"Extract {i+1}: {extract[:50]}...")
    except Exception as e:
        error_msg = f"Error generating extracts: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 3: ALIGN - Match transcript segments with timing using CrewAI
    logger.info("STAGE 3: Aligning transcript segments with timing")
    
    try:
        # Process with crew.py to match transcripts with timestamps
        crew.main(extracts_data)
        logger.info("Alignment completed successfully")
    except Exception as e:
        error_msg = f"Error during transcript alignment: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 4: CLIP - Extract video clips
    logger.info("STAGE 4: Extracting video clips")
    
    try:
        crew_output_folder_path = Path(crew_output_folder)
        output_video_folder_path = Path(output_video_folder)
        
        # Extract clips using subtitle timings
        clip_count = 0
        for srt_file in crew_output_folder_path.glob('*.srt'):
            clipper.main(input_video_path, str(srt_file), str(output_video_folder_path), aspect_ratio_choice)
            logger.info(f"Processed {input_video_path} with {srt_file}")
            clip_count += 1
            
        if clip_count == 0:
            logger.warning("No subtitle files found for clipping")
            return False
        else:
            logger.info(f"Created {clip_count} clips")
    except Exception as e:
        error_msg = f"Error during video clipping: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 5: SUBTITLE - Burn subtitles into videos
    logger.info("STAGE 5: Adding subtitles to videos")
    
    try:
        output_video_folder_path = Path(output_video_folder)
        crew_output_folder_path = Path(crew_output_folder)
        
        subtitle_count = 0
        for video_file in output_video_folder_path.glob('*_trimmed.mp4'):
            base_name = video_file.stem.replace('_trimmed', '')
            
            # Look for corresponding subtitle file
            matching_srt_files = list(crew_output_folder_path.glob(f'*{base_name}*.srt'))
            if not matching_srt_files:
                matching_srt_files = list(crew_output_folder_path.glob('*.srt'))
            
            if matching_srt_files:
                srt_file = matching_srt_files[0]
                subtitler.process_video_and_subtitles(str(video_file), str(srt_file), subtitler_output_folder)
                logger.info(f"Added subtitles to {video_file}")
                subtitle_count += 1
            else:
                logger.warning(f"No matching subtitle file found for {video_file}")
        
        if subtitle_count == 0:
            logger.warning("No videos were subtitled")
            return False
        else:
            logger.info(f"Added subtitles to {subtitle_count} videos")
    except Exception as e:
        error_msg = f"Error during subtitle burning: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # Complete
    logger.info(f"All processing completed. Final output saved in {subtitler_output_folder}")
    return True

def main():
    """Main entry point"""
    try:
        success = process_test_video()
        
        if success:
            logger.info("Processing completed successfully!")
            return 0
        else:
            logger.error("Processing failed. Check the logs for details.")
            return 1
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user.")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 