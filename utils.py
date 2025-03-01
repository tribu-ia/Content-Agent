# Standard library imports
import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime

# Third party imports
import lockfile

def setup_logging(level=logging.INFO):
    """Set up logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("viral_clips.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("viral_clips")

def wait_for_file(filepath, max_retries=5, retry_interval=1):
    """
    This function checks if a file exists and is readable with retry mechanism.

    Args:
        filepath: Path to the file to check
        max_retries: Maximum number of retry attempts
        retry_interval: Time in seconds between retries
    Returns:
        bool: True if file is available and readable, False otherwise
    """
    # First try using lockfile
    try:
        lock = lockfile.FileLock(filepath)
        while not lock.i_am_locking():
            try:
                lock.acquire(timeout=1)  # wait for 1 second
            except lockfile.LockTimeout:
                pass
        return True
    except Exception as e:
        logging.warning(f"Lockfile error for {filepath}: {e}. Falling back to existence check.")
    
    # Fall back to checking file existence and readability
    for attempt in range(max_retries):
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    # Try to read first line to verify file is accessible
                    f.readline()
                return True
            else:
                if attempt < max_retries - 1:
                    logging.warning(f"File {filepath} not found. Retrying in {retry_interval}s ({attempt+1}/{max_retries})")
                    time.sleep(retry_interval)
                else:
                    logging.error(f"File does not exist after {max_retries} attempts: {filepath}")
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(f"Error accessing file {filepath}: {e}. Retrying in {retry_interval}s ({attempt+1}/{max_retries})")
                time.sleep(retry_interval)
            else:
                logging.error(f"Error accessing file after {max_retries} attempts: {e}")
    return False

def create_directories(directories):
    """
    Create multiple directories if they don't exist
    
    Args:
        directories: List of directory paths to create
    """
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.debug(f"Created directory: {directory}")

def save_checkpoint(checkpoint_data, filename="checkpoint.json"):
    """
    Save processing checkpoint to a file
    
    Args:
        checkpoint_data: Dictionary with checkpoint information
        filename: Name of the checkpoint file
    """
    checkpoint_dir = Path("./checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    checkpoint_path = checkpoint_dir / filename
    
    # Add timestamp
    checkpoint_data["timestamp"] = datetime.now().isoformat()
    
    try:
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        logging.info(f"Checkpoint saved: {checkpoint_path}")
        return True
    except Exception as e:
        logging.error(f"Error saving checkpoint: {e}")
        return False

def load_checkpoint(filename="checkpoint.json"):
    """
    Load processing checkpoint from a file
    
    Args:
        filename: Name of the checkpoint file
    
    Returns:
        dict: Checkpoint data or None if file doesn't exist or error occurs
    """
    checkpoint_path = Path("./checkpoints") / filename
    
    if not os.path.exists(checkpoint_path):
        logging.warning(f"Checkpoint file not found: {checkpoint_path}")
        return None
    
    try:
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
        logging.info(f"Checkpoint loaded: {checkpoint_path}")
        return checkpoint_data
    except Exception as e:
        logging.error(f"Error loading checkpoint: {e}")
        return None

def get_timestamp():
    """Get formatted timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def retry_operation(operation, max_retries=3, retry_interval=2, *args, **kwargs):
    """
    Retry an operation with exponential backoff
    
    Args:
        operation: Function to execute
        max_retries: Maximum number of retry attempts
        retry_interval: Initial time between retries (doubles with each attempt)
        *args, **kwargs: Arguments to pass to the operation
        
    Returns:
        Result of the operation or None if all attempts fail
    """
    for attempt in range(max_retries):
        try:
            result = operation(*args, **kwargs)
            return result
        except Exception as e:
            wait_time = retry_interval * (2 ** attempt)
            if attempt < max_retries - 1:
                logging.warning(f"Operation failed: {e}. Retrying in {wait_time}s ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                logging.error(f"Operation failed after {max_retries} attempts: {e}")
                raise