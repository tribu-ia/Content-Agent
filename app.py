# Standard library imports
import os
import warnings
import logging
from pathlib import Path
import argparse

# Third party imports
from dotenv import load_dotenv
from send2trash import send2trash

# Local application imports
from utils import setup_logging, create_directories
from workflow import WorkflowController

# Setup logging
logger = setup_logging()

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# List of required environment variables
required_vars = ['OPENAI_API_KEY']

"""
This for loop checks if the required environment variables are set. 
If any of the required environment variables are set to 'None', an EnvironmentError is raised.
"""
for var in required_vars:
    value = os.getenv(var)
    if value is None or value == 'None':
        raise EnvironmentError(f"Required environment variable {var} is not set or is set to 'None'.")

def clean_output_directories(directories):
    """Clean output directories by moving files to trash"""
    for directory in directories:
        if not os.path.exists(directory):
            continue
            
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    send2trash(file_path)
                    logger.info(f"Moved {file_path} to trash")
            except Exception as e:
                logger.error(f"Error while moving {file_path} to trash: {e}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Viral Clips Workflow")
    
    # Input source options
    parser.add_argument('--youtube', '-y', type=str, help="YouTube URL to process")
    parser.add_argument('--input-file', '-i', type=str, help="Local video file to process")
    parser.add_argument('--input-dir', '-d', type=str, default="./input_files", help="Directory containing video files to process")
    
    # Platform targeting
    parser.add_argument('--platforms', '-p', type=str, nargs='+', 
                        choices=['instagram', 'tiktok', 'youtube', 'linkedin'], 
                        default=['instagram', 'tiktok', 'youtube'],
                        help="Target platforms for content")
    
    # Processing options
    parser.add_argument('--clean', '-c', action='store_true', help="Clean output directories before processing")
    parser.add_argument('--state-file', '-s', type=str, help="Load workflow state from file")
    
    return parser.parse_args()

def main():
    """Main entry point for the application"""
    args = parse_arguments()
    
    # Directory setup
    directories = {
        'input': './input_files',
        'output': './output',
        'output_segments': './output/segments',
        'output_platform': './output/platform_versions',
        'state': './state'
    }
    
    # Create directories
    create_directories(list(directories.values()))
    
    # Clean directories if requested
    if args.clean:
        clean_output_directories([
            directories['output_segments'],
            directories['output_platform']
        ])
    
    # Initialize workflow controller
    workflow = WorkflowController()
    
    # Load state if provided
    if args.state_file and os.path.exists(args.state_file):
        workflow.load_state(args.state_file)
        logger.info(f"Loaded workflow state from {args.state_file}")
    
    # Process YouTube URL if provided
    if args.youtube:
        # TODO: Implement YouTube download functionality
        logger.info(f"Processing YouTube URL: {args.youtube}")
        # This would be replaced with actual implementation
        # video_path = download_youtube_video(args.youtube, directories['input'])
        # if video_path:
        #     workflow.process_video(video_path, args.platforms)
        # else:
        #     logger.error("Failed to download YouTube video")
        logger.info("YouTube processing not yet implemented")
        return
    
    # Process specific input file if provided
    elif args.input_file:
        if os.path.exists(args.input_file):
            logger.info(f"Processing input file: {args.input_file}")
            workflow.process_video(args.input_file, args.platforms)
        else:
            logger.error(f"Input file not found: {args.input_file}")
            return
    
    # Process all files in input directory
    else:
        input_dir = args.input_dir
        if not os.path.exists(input_dir):
            logger.error(f"Input directory not found: {input_dir}")
            return
            
        input_files = list(Path(input_dir).glob('*.mp4'))
        if not input_files:
            logger.error(f"No video files found in directory: {input_dir}")
            return
            
        logger.info(f"Processing {len(input_files)} video files from {input_dir}")
        for video_file in input_files:
            result = workflow.process_video(str(video_file), args.platforms)
            logger.info(f"Processed {video_file.name}: {result}")
    
    # Save final state
    workflow.save_state()
    
    logger.info("Processing complete. Final output saved in output directory.")

if __name__ == "__main__":
    main()