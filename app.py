# Standard library imports
import os
import warnings
import sys
import argparse
from pathlib import Path
import traceback
from send2trash import send2trash

# Third party imports
from dotenv import load_dotenv

# Local application imports
import clipper
import subtitler
import crew
from ytdl import main as ytdl_main
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
    
    # Initialize checkpoint data
    checkpoint = {
        "stage": STAGES["setup"],
        "input_video": None,
        "aspect_ratio": None,
        "extracts_data": None,
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
        
        # Update checkpoint
        checkpoint["stage"] = STAGES["transcribe"]
        checkpoint["input_video"] = input_video_path
        checkpoint["aspect_ratio"] = aspect_ratio_choice
        save_checkpoint(checkpoint)
    else:
        # Retrieve from checkpoint
        input_video_path = checkpoint["input_video"]
        aspect_ratio_choice = checkpoint["aspect_ratio"]
    
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