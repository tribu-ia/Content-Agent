#!/usr/bin/env python

# Standard library imports
import os
import warnings
import sys
import traceback
import json
from pathlib import Path

# Third party imports
from dotenv import load_dotenv

# Local application imports
from chunker import VideoChunker
from utils import setup_logging, create_directories

# Setup logging
logger = setup_logging()

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

def test_chunker_functionality():
    """Test basic VideoChunker class functionality"""
    # Folder setup
    input_folder = './input_files'
    chunks_folder = './test_output/chunks'
    
    # Create necessary directories
    create_directories([chunks_folder])
    
    # Clean output directory
    for file in Path(chunks_folder).glob('*'):
        if file.is_file():
            file.unlink()
            logger.info(f"Removed {file}")
    
    # Find a video file to test
    video_files = list(Path(input_folder).glob('*.mp4'))
    if not video_files:
        logger.error(f"No video files found in {input_folder}")
        return False
    
    input_video_path = str(video_files[0])
    logger.info(f"Using video file: {input_video_path}")
    
    # Initialize the chunker with small chunk size for testing
    chunker = VideoChunker(chunk_size=300, overlap=30)  # 5 min chunks with 30s overlap
    chunker.setup()
    logger.info(f"Initialized chunker with chunk_size=300s, overlap=30s")
    
    # Get video duration
    duration = chunker.get_video_duration(input_video_path)
    if not duration:
        logger.error("Failed to get video duration")
        return False
    
    logger.info(f"Video duration: {duration} seconds ({duration/60:.2f} minutes)")
    
    # Check if video needs chunking
    needs_chunking = chunker.needs_chunking(input_video_path)
    logger.info(f"Video needs chunking: {needs_chunking}")
    
    # Create chunks
    logger.info("Creating video chunks...")
    chunk_paths = chunker.split_video(input_video_path)
    
    if not chunk_paths:
        logger.error("Failed to create chunks")
        return False
    
    logger.info(f"Successfully created {len(chunk_paths)} chunks")
    for i, path in enumerate(chunk_paths):
        logger.info(f"Chunk {i+1}: {path}")
    
    # Verify manifest file
    if not chunker.manifest_path.exists():
        logger.error("Manifest file not created")
        return False
    
    # Get chunks from manifest
    chunks = chunker.get_chunks()
    logger.info(f"Retrieved {len(chunks)} chunks from manifest")
    
    # Test marking a chunk as processed
    if chunks:
        result = chunker.mark_chunk_processed(chunks[0]["index"])
        logger.info(f"Marked chunk 0 as processed: {result}")
        
        # Verify the chunk was marked as processed
        updated_chunks = chunker.get_chunks()
        if updated_chunks[0]["processed"]:
            logger.info("Successfully verified chunk was marked as processed")
        else:
            logger.error("Failed to mark chunk as processed")
            return False
    
    # Test timestamp adjustment
    test_timestamp = "00:01:30,500"
    chunk_start_time = 60.0  # 1 minute offset
    adjusted = chunker.adjust_timestamp(test_timestamp, chunk_start_time)
    logger.info(f"Original timestamp: {test_timestamp}, Adjusted: {adjusted}")
    
    # Test subtitle timestamp adjustment
    test_srt = """1
00:00:01,000 --> 00:00:05,000
This is a test subtitle

2
00:00:06,000 --> 00:00:10,000
This is another test subtitle
"""
    adjusted_srt = chunker.adjust_subtitle_timestamps(test_srt, chunk_start_time)
    logger.info("Successfully tested subtitle timestamp adjustment")
    logger.info(f"Original SRT:\n{test_srt}")
    logger.info(f"Adjusted SRT:\n{adjusted_srt}")
    
    return True

def main():
    """Main entry point"""
    try:
        success = test_chunker_functionality()
        
        if success:
            logger.info("Chunker test completed successfully!")
            return 0
        else:
            logger.error("Chunker test failed. Check the logs for details.")
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