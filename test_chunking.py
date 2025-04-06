#!/usr/bin/env python

# Standard library imports
import os
import warnings
import sys
import traceback
import json
import shutil
from pathlib import Path

# Third party imports
from dotenv import load_dotenv

# Local application imports
import clipper
import subtitler
import crew
from local_transcribe import local_whisper_process
import extracts
from chunker import VideoChunker
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

# Load environment variables - use the existing .env file
load_dotenv(dotenv_path='.env')

# Verify API keys
required_keys = ['GEMINI_API_KEY', 'OPENAI_API_KEY']
for key in required_keys:
    if not os.getenv(key):
        logger.warning(f"Warning: {key} is not set in your .env file")
        logger.warning(f"Please create or update your .env file with your API keys before running this test")

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

def test_chunking_pipeline():
    """Test processing a single chunk through the complete pipeline"""
    # Folder setup
    input_folder = './input_files'
    output_video_folder = './test_output/clipper_output'
    crew_output_folder = './crew_output'
    whisper_output_folder = './test_output/whisper_output'
    subtitler_output_folder = './test_output/subtitler_output'
    chunks_folder = './test_output/chunks'
    chunks_output_folder = './test_output/chunks_output'
    
    # Create necessary directories
    folders = [
        input_folder, output_video_folder, crew_output_folder, 
        whisper_output_folder, subtitler_output_folder,
        chunks_folder, chunks_output_folder
    ]
    create_directories(folders)
    
    # Clean output directories
    for folder in [output_video_folder, whisper_output_folder, subtitler_output_folder,
                  chunks_folder, chunks_output_folder]:
        clean_output_folder(folder)
        logger.info(f"Cleaned output folder: {folder}")
    
    # Find a video file to test
    video_files = list(Path(input_folder).glob('*.mp4'))
    if not video_files:
        logger.error(f"No video files found in {input_folder}")
        return False
    
    input_video_path = str(video_files[0])
    logger.info(f"Using video file: {input_video_path}")
    
    # Set aspect ratio choice (1=original, 2=square)
    aspect_ratio_choice = '1'
    
    # Initialize the chunker
    chunker = VideoChunker(chunk_size=300, overlap=30)  # Use smaller chunk size (5 min) for testing
    chunker.setup()
    logger.info(f"Initialized chunker with chunk_size=300s, overlap=30s")
    
    # STAGE 1: Create a single chunk
    logger.info("STAGE 1: Creating a test chunk")
    try:
        # Force create a single chunk
        chunk_paths = chunker.split_video(input_video_path)
        if not chunk_paths or len(chunk_paths) == 0:
            logger.error("Failed to create chunks")
            return False
        
        # Use only the first chunk for testing
        test_chunk_path = chunk_paths[0]
        chunk_data = chunker.get_chunks()[0]
        chunk_index = chunk_data["index"]
        chunk_start_time = chunk_data["start_time"]
        
        logger.info(f"Created test chunk: {test_chunk_path}")
        logger.info(f"Chunk index: {chunk_index}, Start time: {chunk_start_time}")
    except Exception as e:
        error_msg = f"Error creating chunk: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 2: TRANSCRIBE - Generate transcription using Whisper
    logger.info("STAGE 2: Transcribing chunk")
    
    try:
        # Transcribe the chunk
        local_whisper_process(os.path.dirname(test_chunk_path), whisper_output_folder)
        
        # Save transcription to chunks_output for later use
        for file in os.listdir(whisper_output_folder):
            if file.endswith('.srt') or file.endswith('.txt'):
                src_path = os.path.join(whisper_output_folder, file)
                dst_path = os.path.join(chunks_output_folder, f"chunk_{chunk_index}_{file}")
                shutil.copy(src_path, dst_path)
                logger.info(f"Saved transcription to {dst_path}")
        
        logger.info("Transcription completed successfully")
    except Exception as e:
        error_msg = f"Error during transcription: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 3: EXTRACT - Generate viral extracts using GPT
    logger.info("STAGE 3: Generating viral extracts")
    
    all_extracts = []
    try:
        extracts_data = retry_operation(extracts.main)
        if extracts_data is None:
            logger.error("Failed to generate extracts")
            return False
        
        # Add chunk metadata to extracts
        for i in range(len(extracts_data)):
            all_extracts.append({
                "text": extracts_data[i],
                "chunk_index": chunk_index,
                "chunk_start_time": chunk_start_time
            })
        
        logger.info(f"Generated {len(extracts_data)} extracts")
        for i, extract in enumerate(extracts_data):
            logger.info(f"Extract {i+1}: {extract[:50]}...")
            
        # Save extracts to a test file
        with open('test_output/extracts.json', 'w') as f:
            json.dump(all_extracts, f, indent=2)
            
    except Exception as e:
        error_msg = f"Error generating extracts: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 4: ALIGN - Match transcript segments with timing using CrewAI
    logger.info("STAGE 4: Aligning transcript segments with timing")
    
    try:
        # Process with crew.py to match transcripts with timestamps
        crew.main([extract["text"] for extract in all_extracts])
        
        # Find the generated SRT files
        srt_files = list(Path(crew_output_folder).glob('*.srt'))
        if not srt_files:
            logger.error("No SRT files generated")
            return False
            
        # Adjust timestamps for each SRT file
        for srt_file in srt_files:
            # Read the SRT content
            with open(srt_file, 'r') as f:
                srt_content = f.read()
                
            # Adjust timestamps to account for chunk position
            adjusted_srt_content = chunker.adjust_subtitle_timestamps(
                srt_content, chunk_start_time)
                
            # Save adjusted SRT
            adjusted_srt_path = os.path.join(
                crew_output_folder, 
                f"adjusted_chunk_{chunk_index}_{srt_file.name}"
            )
                
            with open(adjusted_srt_path, 'w') as f:
                f.write(adjusted_srt_content)
                
            logger.info(f"Adjusted timestamps in {adjusted_srt_path}")
            
            # Add SRT path to extract info
            for extract in all_extracts:
                extract["srt_path"] = adjusted_srt_path
                
        logger.info("Alignment completed successfully")
    except Exception as e:
        error_msg = f"Error during transcript alignment: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 5: CLIP - Extract video clips from original video
    logger.info("STAGE 5: Extracting video clips")
    
    try:
        # Use the original video with the adjusted SRT files
        original_video = input_video_path
        
        for extract in all_extracts:
            if "srt_path" in extract:
                srt_path = extract["srt_path"]
                clipper.main(original_video, srt_path, output_video_folder, aspect_ratio_choice)
                logger.info(f"Processed clip from original video using {srt_path}")
        
        # Check if clips were created
        clip_count = len(list(Path(output_video_folder).glob('*_trimmed.mp4')))
        if clip_count == 0:
            logger.warning("No clips were created")
            return False
        else:
            logger.info(f"Created {clip_count} clips")
    except Exception as e:
        error_msg = f"Error during video clipping: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False
    
    # STAGE 6: SUBTITLE - Burn subtitles into videos
    logger.info("STAGE 6: Adding subtitles to videos")
    
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
    logger.info(f"Test completed successfully. Final output saved in {subtitler_output_folder}")
    return True

def main():
    """Main entry point"""
    try:
        success = test_chunking_pipeline()
        
        if success:
            logger.info("Chunking test completed successfully!")
            return 0
        else:
            logger.error("Chunking test failed. Check the logs for details.")
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