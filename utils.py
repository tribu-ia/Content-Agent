# Standard library imports
import os
import sys
import json
import logging
from pathlib import Path
import datetime
from typing import Dict, List, Any, Optional, Callable
import threading
import queue
from dataclasses import dataclass, asdict, field

# Third party imports
import lockfile

# Setup logging
def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

# File system utilities
def create_directories(directories):
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def get_input_files(input_folder, extension=".mp4"):
    """Get list of input files with specific extension."""
    input_folder_path = Path(input_folder)
    return list(input_folder_path.glob(f'*{extension}'))

def save_json(data, file_path):
    """Save data to JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def load_json(file_path):
    """Load data from JSON file."""
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r') as f:
        return json.load(f)

def get_timestamp():
    """Get current timestamp in a filename-friendly format."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def wait_for_file(filepath):
    """
    This function checks if a file exists and is readable.

    Args:
        filepath: Path to the file to check
    Returns:
        bool: True if file is available and readable, False otherwise
    """
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                # Try to read first line to verify file is accessible
                f.readline()
            return True
        else:
            logging.error(f"File does not exist: {filepath}")
            return False
    except Exception as e:
        logging.error(f"Error accessing file {filepath}: {e}")
        return False

# Shared State / Context Store
class SharedState:
    """Central knowledge repository for agent communication"""
    
    def __init__(self):
        self._state = {}
        self._lock = threading.Lock()
        self._event_subscribers = {}
        
    def set(self, key: str, value: Any) -> None:
        """Set a value in the shared state and notify subscribers"""
        with self._lock:
            self._state[key] = value
            self._notify_subscribers(key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the shared state"""
        with self._lock:
            return self._state.get(key, default)
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple values in the shared state"""
        with self._lock:
            self._state.update(data)
            for key, value in data.items():
                self._notify_subscribers(key, value)
    
    def subscribe(self, key: str, callback: Callable[[str, Any], None]) -> None:
        """Subscribe to changes on a specific key"""
        with self._lock:
            if key not in self._event_subscribers:
                self._event_subscribers[key] = []
            self._event_subscribers[key].append(callback)
    
    def _notify_subscribers(self, key: str, value: Any) -> None:
        """Notify subscribers of changes to a key"""
        subscribers = self._event_subscribers.get(key, [])
        for callback in subscribers:
            callback(key, value)
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire state (for debugging/logging)"""
        with self._lock:
            return self._state.copy()
    
    def save(self, file_path: str) -> None:
        """Save state to file"""
        with self._lock:
            save_json(self._state, file_path)
    
    def load(self, file_path: str) -> None:
        """Load state from file"""
        loaded_state = load_json(file_path)
        if loaded_state:
            with self._lock:
                self._state = loaded_state
                for key, value in self._state.items():
                    self._notify_subscribers(key, value)

# Quality tracking
@dataclass
class QualityMetrics:
    """Quality metrics for tracking improvement"""
    
    content_relevance: float = 0.0
    technical_quality: float = 0.0
    brand_alignment: float = 0.0
    platform_optimization: float = 0.0
    engagement_potential: float = 0.0
    improvements: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_improvement(self, metric: str, from_value: float, to_value: float, 
                       description: str, timestamp: Optional[str] = None):
        """Track an improvement in a specific metric"""
        if timestamp is None:
            timestamp = get_timestamp()
            
        improvement = {
            'metric': metric,
            'from_value': from_value,
            'to_value': to_value,
            'change': to_value - from_value,
            'description': description,
            'timestamp': timestamp
        }
        self.improvements.append(improvement)
        
        # Update the corresponding metric
        if hasattr(self, metric):
            setattr(self, metric, to_value)
            
    def get_latest_improvements(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get the most recent improvements"""
        return sorted(self.improvements, key=lambda x: x['timestamp'], reverse=True)[:count]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

# Base Agent class
class Agent:
    """Base class for all workflow agents"""
    
    def __init__(self, name: str, shared_state: SharedState):
        self.name = name
        self.shared_state = shared_state
        self.logger = logging.getLogger(name)
    
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """Process method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement process()")
    
    def log_result(self, result: Dict[str, Any]) -> None:
        """Log processing result"""
        self.logger.info(f"{self.name} completed processing: {result.get('status', 'unknown')}")