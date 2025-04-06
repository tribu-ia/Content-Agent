# Standard library imports
import os
import warnings
import sys
import argparse
from pathlib import Path
import traceback
from send2trash import send2trash
import shutil

# Third party imports
from dotenv import load_dotenv

# Local application imports
import clipper
import subtitler
import crew
from ytdl import main as ytdl_main
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

# Load environment variables
load_dotenv()

# Processing stages
STAGES = {
    "setup": 0,
    "input": 1,
    "transcribe": 2,
    "extract": 3,
    "align": 4,
    "clip": 5,
    "subtitle": 6,
    "complete": 7
}

def validate_environment():
    """Validate required environment variables and dependencies"""
    # Check API keys
    required_vars = ['OPENAI_API_KEY', 'GEMINI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value is None or value == 'None':
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"Required environment variable(s) not set: {', '.join(missing_vars)}"
        logger.error(error_msg)
        return False, error_msg
    
    # Check for ffmpeg
    try:
        import ffmpeg
        logger.info("FFmpeg python binding found")
    except ImportError:
        error_msg = "FFmpeg python binding not installed. Please install ffmpeg-python."
        logger.error(error_msg)
        return False, error_msg
    
    # Check if ffmpeg is in PATH
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info("FFmpeg binary found in PATH")
    except (subprocess.SubprocessError, FileNotFoundError):
        error_msg = "FFmpeg binary not found in PATH. Please install FFmpeg."
        logger.error(error_msg)
        return False, error_msg
    
    return True, "Environment validated successfully"

def get_aspect_ratio_choice():
    """Get user choice for video aspect ratio"""
    while True:
        choice = input("Choose aspect ratio for all videos: (1) Keep as original, (2) 1:1 (square): ")
        if choice in ['1', '2']:
            return choice
        print("Invalid choice. Please enter 1 or 2.")

def clean_output_folder(folder_path):
    """Clean output folder by moving files to trash"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return
    
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                send2trash(file_path)
                logger.info(f"Moved {file_path} to trash")
        except Exception as e:
            logger.error(f"Error while moving {file_path} to trash: {e}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Viral Clips Generator")
    
    # Input source
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('--youtube', '-y', type=str, help="YouTube URL to download and process")
    input_group.add_argument('--input-file', '-i', type=str, help="Local video file to process")
    
    # Processing options
    parser.add_argument('--aspect-ratio', '-a', choices=['1', '2'], 
                        help="Aspect ratio: 1=original, 2=square (1:1)")
    parser.add_argument('--clean', '-c', action='store_true', help="Clean output directories before processing")
    
    # Chunking options
    parser.add_argument('--disable-chunking', '-d', action='store_true', 
                        help="Disable automatic chunking for long videos")
    parser.add_argument('--chunk-size', type=int, default=600,
                        help="Size of each chunk in seconds (default: 600 = 10 minutes)")
    parser.add_argument('--chunk-overlap', type=int, default=30,
                        help="Overlap between chunks in seconds (default: 30)")
    parser.add_argument('--force-chunking', '-f', action='store_true',
                        help="Force chunking even for short videos")
    
    # Restart options
    parser.add_argument('--restart', '-r', action='store_true', help="Restart from last saved checkpoint")
    parser.add_argument('--stage', '-s', choices=list(STAGES.keys())[:-1],
                        help="Restart from specific stage (setup, input, transcribe, extract, align, clip, subtitle)")
    
    return parser.parse_args()

def process_video(args=None):
    """Main processing function with checkpoint/restart capability"""
    # Folder setup
    input_folder = './input_files'
    output_video_folder = './clipper_output'
    crew_output_folder = './crew_output'
    whisper_output_folder = './whisper_output'
    subtitler_output_folder = './subtitler_output'
    checkpoints_folder = './checkpoints'

    # Create necessary directories
    folders = [
        input_folder, output_video_folder, crew_output_folder, 
        whisper_output_folder, subtitler_output_folder, checkpoints_folder
    ]
    create_directories(folders)
    
    # Initialize chunker with custom parameters if provided
    chunk_size = 600  # Default 10 minutes
    chunk_overlap = 30  # Default 30 seconds
    
    if args:
        if args.chunk_size:
            chunk_size = args.chunk_size
        if args.chunk_overlap:
            chunk_overlap = args.chunk_overlap
            
    chunker = VideoChunker(chunk_size=chunk_size, overlap=chunk_overlap)
    chunker.setup()
    
    # Initialize checkpoint data
    checkpoint = {
        "stage": STAGES["setup"],
        "input_video": None,
        "aspect_ratio": None,
        "extracts_data": None,
        "chunking_enabled": False,
        "errors": []
    }
    
    # Handle restart from checkpoint
    starting_stage = STAGES["setup"]
    if args and args.restart:
        loaded_checkpoint = load_checkpoint()
        if loaded_checkpoint:
            checkpoint = loaded_checkpoint
            starting_stage = checkpoint["stage"]
            logger.info(f"Restarting from stage: {list(STAGES.keys())[starting_stage]}")
    elif args and args.stage:
        starting_stage = STAGES[args.stage]
        logger.info(f"Starting from specified stage: {args.stage}")
    
    # Clean outputs if requested
    if args and args.clean:
        folders_to_clean = [output_video_folder, crew_output_folder, whisper_output_folder, subtitler_output_folder]
        for folder in folders_to_clean:
            clean_output_folder(folder)
            logger.info(f"Cleaned output folder: {folder}")
    
    # STAGE 0: SETUP - Validate environment
    if starting_stage <= STAGES["setup"]:
        logger.info("STAGE 0: Setting up and validating environment")
        valid, message = validate_environment()
        if not valid:
            logger.error(f"Environment validation failed: {message}")
            return False
        
        # Update checkpoint
        checkpoint["stage"] = STAGES["input"]
        save_checkpoint(checkpoint)
    
    # STAGE 1: INPUT - Get input video
    input_video_path = None
    
    if starting_stage <= STAGES["input"]:
        logger.info("STAGE 1: Processing input video")
        
        # If restarting and we already have an input video, use it
        if checkpoint.get("input_video") and os.path.exists(checkpoint["input_video"]):
            input_video_path = checkpoint["input_video"]
            logger.info(f"Using existing input video from checkpoint: {input_video_path}")
        else:
            # Handle command line arguments for input
            if args:
                if args.youtube:
                    logger.info(f"Processing YouTube URL: {args.youtube}")
                    try:
                        # Download the YouTube video
                        ytdl_main(args.youtube, input_folder, whisper_output_folder, whisper_output_folder)
                        
                        # Find the downloaded file
                        video_files = list(Path(input_folder).glob('*.mp4'))
                        if video_files:
                            input_video_path = str(video_files[0])
                            logger.info(f"Downloaded YouTube video: {input_video_path}")
                        else:
                            logger.error("Failed to find downloaded YouTube video")
                            return False
                    except Exception as e:
                        logger.error(f"Error downloading YouTube video: {e}")
                        checkpoint["errors"].append(f"YouTube download error: {str(e)}")
                        save_checkpoint(checkpoint)
                        return False
                        
                elif args.input_file:
                    if not os.path.exists(args.input_file):
                        logger.error(f"Input file not found: {args.input_file}")
                        return False
                    input_video_path = args.input_file
                    logger.info(f"Using specified input file: {input_video_path}")
                else:
                    # Look for video files in the input folder
                    video_files = list(Path(input_folder).glob('*.mp4'))
                    if not video_files:
                        logger.error(f"No video files found in {input_folder}")
                        return False
                    input_video_path = str(video_files[0])
                    logger.info(f"Using existing video file: {input_video_path}")
            else:
                # Interactive mode: let user choose input method
                while True:
                    logger.info("Please select an option to proceed:")
                    logger.info("1: Submit a YouTube Video Link")
                    logger.info("2: Use an existing video file")
                    choice = input("Please choose either option 1 or 2: ")

                    if choice == '1':
                        logger.info("Submitting a YouTube Video Link")
                        url = input("Enter the YouTube URL: ")
                        try:
                            ytdl_main(url, input_folder, whisper_output_folder, whisper_output_folder)
                            video_files = list(Path(input_folder).glob('*.mp4'))
                            if video_files:
                                input_video_path = str(video_files[0])
                                logger.info(f"Downloaded YouTube video: {input_video_path}")
                                break
                            else:
                                logger.error("Failed to find downloaded YouTube video")
                        except Exception as e:
                            logger.error(f"Error downloading YouTube video: {e}")
                            checkpoint["errors"].append(f"YouTube download error: {str(e)}")
                    elif choice == '2':
                        logger.info("Using an existing video file")
                        video_files = list(Path(input_folder).glob('*.mp4'))
                        if not video_files:
                            logger.error(f"No video files found in the folder: {input_folder}")
                            continue
                        input_video_path = str(video_files[0])
                        logger.info(f"Using existing video file: {input_video_path}")
                        break
                    else:
                        logger.info("Invalid choice. Please try again.")
        
        # Get aspect ratio choice
        if args and args.aspect_ratio:
            aspect_ratio_choice = args.aspect_ratio
        elif checkpoint.get("aspect_ratio"):
            aspect_ratio_choice = checkpoint["aspect_ratio"]
        else:
            aspect_ratio_choice = get_aspect_ratio_choice()
        
        # Check if video needs chunking
        use_chunking = False
        
        # First check if chunking is forced or disabled via command line
        if args and args.force_chunking:
            logger.info("Chunking forced via command line")
            use_chunking = True
        elif args and args.disable_chunking:
            logger.info("Chunking disabled via command line")
            use_chunking = False
        # Otherwise check video length
        elif chunker.needs_chunking(input_video_path):
            logger.info(f"Video is longer than 60 minutes, chunking will be used")
            use_chunking = True
        else:
            logger.info("Video is short enough to process without chunking")
            use_chunking = False
        
        checkpoint["chunking_enabled"] = use_chunking
        
        # If chunking is enabled, split the video
        if use_chunking:
            # Split the video into chunks
            chunk_paths = chunker.split_video(input_video_path)
            if not chunk_paths:
                logger.error("Failed to chunk video")
                checkpoint["errors"].append("Video chunking failed")
                save_checkpoint(checkpoint)
                return False
                
            logger.info(f"Video split into {len(chunk_paths)} chunks")
            checkpoint["original_video"] = input_video_path
        
        # Update checkpoint
        checkpoint["stage"] = STAGES["transcribe"]
        checkpoint["input_video"] = input_video_path
        checkpoint["aspect_ratio"] = aspect_ratio_choice
        save_checkpoint(checkpoint)
    else:
        # Retrieve from checkpoint
        input_video_path = checkpoint["input_video"]
        aspect_ratio_choice = checkpoint["aspect_ratio"]
    
    # Check if we're using chunking mode
    chunking_enabled = checkpoint.get("chunking_enabled", False)
    
    if chunking_enabled:
        return process_chunked_video(chunker, checkpoint, starting_stage, args)
    
    # If not using chunking, continue with the normal processing flow
    # STAGE 2: TRANSCRIBE - Generate transcription using Whisper
    if starting_stage <= STAGES["transcribe"]:
        logger.info("STAGE 2: Transcribing video")
        
        try:
            # Clean whisper output to ensure fresh start
            clean_output_folder(whisper_output_folder)
            
            # Transcribe the video
            local_whisper_process(os.path.dirname(input_video_path), whisper_output_folder)
            
            # Update checkpoint
            checkpoint["stage"] = STAGES["extract"]
            save_checkpoint(checkpoint)
        except Exception as e:
            error_msg = f"Error during transcription: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            checkpoint["errors"].append(error_msg)
            save_checkpoint(checkpoint)
            return False
    
    # STAGE 3: EXTRACT - Generate viral extracts using GPT
    extracts_data = None
    if starting_stage <= STAGES["extract"]:
        logger.info("STAGE 3: Generating viral extracts")
        
        if checkpoint.get("extracts_data"):
            extracts_data = checkpoint["extracts_data"]
            logger.info("Using extracts data from checkpoint")
        else:
            try:
                extracts_data = retry_operation(extracts.main)
                if extracts_data is None:
                    logger.error("Failed to generate extracts")
                    checkpoint["errors"].append("Extract generation failed")
                    save_checkpoint(checkpoint)
                    return False
                
                # Update checkpoint
                checkpoint["extracts_data"] = extracts_data
                checkpoint["stage"] = STAGES["align"]
                save_checkpoint(checkpoint)
            except Exception as e:
                error_msg = f"Error generating extracts: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                checkpoint["errors"].append(error_msg)
                save_checkpoint(checkpoint)
                return False
    else:
        # Retrieve from checkpoint
        extracts_data = checkpoint["extracts_data"]
    
    # STAGE 4: ALIGN - Match transcript segments with timing using CrewAI
    if starting_stage <= STAGES["align"]:
        logger.info("STAGE 4: Aligning transcript segments with timing")
        
        try:
            # Process with crew.py to match transcripts with timestamps
            crew.main(extracts_data)
            
            # Update checkpoint
            checkpoint["stage"] = STAGES["clip"]
            save_checkpoint(checkpoint)
        except Exception as e:
            error_msg = f"Error during transcript alignment: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            checkpoint["errors"].append(error_msg)
            save_checkpoint(checkpoint)
            return False
    
    # STAGE 5: CLIP - Extract video clips
    if starting_stage <= STAGES["clip"]:
        logger.info("STAGE 5: Extracting video clips")
        
        try:
            # Process with clipper.py
            input_folder_path = Path(os.path.dirname(input_video_path))
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
            
            # Update checkpoint
            checkpoint["stage"] = STAGES["subtitle"]
            save_checkpoint(checkpoint)
        except Exception as e:
            error_msg = f"Error during video clipping: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            checkpoint["errors"].append(error_msg)
            save_checkpoint(checkpoint)
            return False
    
    # STAGE 6: SUBTITLE - Burn subtitles into videos
    if starting_stage <= STAGES["subtitle"]:
        logger.info("STAGE 6: Adding subtitles to videos")
        
        try:
            # Process with subtitler.py
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
            
            # Update checkpoint
            checkpoint["stage"] = STAGES["complete"]
            save_checkpoint(checkpoint)
        except Exception as e:
            error_msg = f"Error during subtitle burning: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            checkpoint["errors"].append(error_msg)
            save_checkpoint(checkpoint)
            return False
    
    # Complete
    logger.info(f"All videos processed. Final output saved in {subtitler_output_folder}")
    return True

def process_chunked_video(chunker, checkpoint, starting_stage, args):
    """Process a video that has been split into chunks"""
    logger.info("Processing video in chunks")
    
    # Get the chunks from the manifest
    chunks = chunker.get_chunks()
    if not chunks:
        logger.error("No chunks found in manifest")
        return False
    
    # Set up directories
    input_folder = './input_files'
    output_video_folder = './clipper_output'
    crew_output_folder = './crew_output'
    whisper_output_folder = './whisper_output'
    subtitler_output_folder = './subtitler_output'
    chunks_output_folder = './chunks_output'
    
    # Create chunks_output directory
    os.makedirs(chunks_output_folder, exist_ok=True)
    
    # Process each chunk
    all_extracts = []
    
    for chunk in chunks:
        chunk_index = chunk["index"]
        chunk_path = chunk["path"]
        chunk_start_time = chunk["start_time"]
        
        # Skip already processed chunks if restarting
        if checkpoint.get("processed_chunks") and chunk_index in checkpoint["processed_chunks"]:
            logger.info(f"Skipping already processed chunk {chunk_index}")
            continue
            
        logger.info(f"Processing chunk {chunk_index}: {chunk_path}")
        
        # STAGE 2: TRANSCRIBE the chunk
        if starting_stage <= STAGES["transcribe"]:
            logger.info(f"STAGE 2: Transcribing chunk {chunk_index}")
            
            try:
                # Clean whisper output for this chunk
                clean_output_folder(whisper_output_folder)
                
                # Transcribe the chunk
                local_whisper_process(os.path.dirname(chunk_path), whisper_output_folder)
                
                # Save chunk transcription to chunks_output
                for file in os.listdir(whisper_output_folder):
                    if file.endswith('.srt') or file.endswith('.txt'):
                        src_path = os.path.join(whisper_output_folder, file)
                        dst_path = os.path.join(chunks_output_folder, f"chunk_{chunk_index}_{file}")
                        shutil.copy(src_path, dst_path)
                
            except Exception as e:
                error_msg = f"Error during chunk transcription: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                checkpoint["errors"].append(error_msg)
                save_checkpoint(checkpoint)
                return False
        
        # STAGE 3: EXTRACT - Generate viral extracts for this chunk
        chunk_extracts = None
        if starting_stage <= STAGES["extract"]:
            logger.info(f"STAGE 3: Generating viral extracts for chunk {chunk_index}")
            
            try:
                # Generate extracts for this chunk
                chunk_extracts = retry_operation(extracts.main)
                if chunk_extracts is None:
                    logger.error(f"Failed to generate extracts for chunk {chunk_index}")
                    checkpoint["errors"].append(f"Extract generation failed for chunk {chunk_index}")
                    save_checkpoint(checkpoint)
                    return False
                
                # Add chunk metadata to extracts
                for i in range(len(chunk_extracts)):
                    all_extracts.append({
                        "text": chunk_extracts[i],
                        "chunk_index": chunk_index,
                        "chunk_start_time": chunk_start_time
                    })
                
                # Save all extracts collected so far
                checkpoint["all_extracts"] = all_extracts
                save_checkpoint(checkpoint)
                
            except Exception as e:
                error_msg = f"Error generating extracts for chunk {chunk_index}: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                checkpoint["errors"].append(error_msg)
                save_checkpoint(checkpoint)
                return False
        
        # Mark chunk as processed
        if "processed_chunks" not in checkpoint:
            checkpoint["processed_chunks"] = []
        checkpoint["processed_chunks"].append(chunk_index)
        chunker.mark_chunk_processed(chunk_index)
        save_checkpoint(checkpoint)
    
    # After processing all chunks, select the best extracts
    if not checkpoint.get("all_extracts"):
        logger.error("No extracts found from any chunks")
        return False
    
    # Select the best N extracts from all chunks
    all_chunk_extracts = checkpoint["all_extracts"]
    
    # We want to select the top 3-4 extracts from all chunks
    # For simplicity, let's take the first extract from each chunk, up to 4 extracts
    best_extracts = []
    chunk_indices_used = set()
    
    # First, try to get one extract from each chunk
    for extract in all_chunk_extracts:
        if extract["chunk_index"] not in chunk_indices_used and len(best_extracts) < 4:
            best_extracts.append(extract)
            chunk_indices_used.add(extract["chunk_index"])
    
    # If we have fewer than 3 extracts, add more from chunks already used
    for extract in all_chunk_extracts:
        if len(best_extracts) < 3 and extract not in best_extracts:
            best_extracts.append(extract)
    
    checkpoint["best_extracts"] = best_extracts
    save_checkpoint(checkpoint)
    
    # STAGE 4: ALIGN - Align extracts with timing using CrewAI
    if starting_stage <= STAGES["align"]:
        logger.info("STAGE 4: Aligning selected extracts with timing")
        
        for extract in best_extracts:
            chunk_index = extract["chunk_index"]
            chunk_start_time = extract["chunk_start_time"]
            extract_text = extract["text"]
            
            # Restore the transcription files for this chunk
            chunk_srt = os.path.join(chunks_output_folder, f"chunk_{chunk_index}_subtitles.srt")
            if os.path.exists(chunk_srt):
                with open(chunk_srt, 'r') as f:
                    srt_content = f.read()
                
                with open(os.path.join(whisper_output_folder, "subtitles.srt"), 'w') as f:
                    f.write(srt_content)
            
            chunk_txt = os.path.join(chunks_output_folder, f"chunk_{chunk_index}_transcript.txt")
            if os.path.exists(chunk_txt):
                with open(chunk_txt, 'r') as f:
                    txt_content = f.read()
                
                with open(os.path.join(whisper_output_folder, "transcript.txt"), 'w') as f:
                    f.write(txt_content)
            
            try:
                # Create a single-element list with just this extract
                crew.main([extract_text])
                
                # Find the generated SRT file
                srt_files = list(Path(crew_output_folder).glob('*.srt'))
                if srt_files:
                    latest_srt = max(srt_files, key=os.path.getmtime)
                    
                    # Adjust timestamps to account for chunk position
                    with open(latest_srt, 'r') as f:
                        chunk_srt_content = f.read()
                    
                    adjusted_srt_content = chunker.adjust_subtitle_timestamps(
                        chunk_srt_content, chunk_start_time)
                    
                    # Save adjusted SRT
                    adjusted_srt_path = os.path.join(
                        crew_output_folder, 
                        f"adjusted_chunk_{chunk_index}_{os.path.basename(latest_srt)}"
                    )
                    
                    with open(adjusted_srt_path, 'w') as f:
                        f.write(adjusted_srt_content)
                    
                    # Add to extract info
                    extract["srt_path"] = adjusted_srt_path
                
            except Exception as e:
                error_msg = f"Error aligning extract from chunk {chunk_index}: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                checkpoint["errors"].append(error_msg)
                save_checkpoint(checkpoint)
                # Continue with other extracts
        
        # Update checkpoint with SRT paths
        save_checkpoint(checkpoint)
    
    # STAGE 5: CLIP - Extract clips from original video
    if starting_stage <= STAGES["clip"]:
        logger.info("STAGE 5: Extracting clips from original video")
        
        original_video = checkpoint["original_video"]
        
        try:
            for extract in best_extracts:
                if "srt_path" in extract:
                    srt_path = extract["srt_path"]
                    clipper.main(original_video, srt_path, output_video_folder, checkpoint["aspect_ratio"])
                    logger.info(f"Processed clip from original video using {srt_path}")
            
            # Update checkpoint
            checkpoint["stage"] = STAGES["subtitle"]
            save_checkpoint(checkpoint)
            
        except Exception as e:
            error_msg = f"Error during video clipping: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            checkpoint["errors"].append(error_msg)
            save_checkpoint(checkpoint)
            return False
    
    # STAGE 6: SUBTITLE - Burn subtitles into videos
    if starting_stage <= STAGES["subtitle"]:
        logger.info("STAGE 6: Adding subtitles to videos")
        
        try:
            # Process with subtitler.py
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
            
            # Update checkpoint
            checkpoint["stage"] = STAGES["complete"]
            save_checkpoint(checkpoint)
        except Exception as e:
            error_msg = f"Error during subtitle burning: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            checkpoint["errors"].append(error_msg)
            save_checkpoint(checkpoint)
            return False
    
    # Complete
    logger.info(f"All chunked video processing completed. Final output saved in {subtitler_output_folder}")
    return True

def main():
    """Main entry point with argument parsing and error handling"""
    try:
        args = parse_arguments()
        success = process_video(args)
        
        if success:
            logger.info("Processing completed successfully!")
            return 0
        else:
            logger.error("Processing failed. Check the logs for details.")
            return 1
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user. You can restart from the last checkpoint with --restart")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())