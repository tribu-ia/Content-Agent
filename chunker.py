import os
import json
import logging
from pathlib import Path
import ffmpeg

logger = logging.getLogger(__name__)

class VideoChunker:
    def __init__(self, chunk_size=600, overlap=30):
        """
        Initialize the chunker with specified chunk size and overlap.
        
        Args:
            chunk_size: Size of each chunk in seconds (default: 600 seconds = 10 minutes)
            overlap: Overlap between chunks in seconds (default: 30 seconds)
        """
        self.chunk_size = chunk_size  # 10 minutes in seconds
        self.overlap = overlap  # 30 seconds
        self.chunks_dir = Path("./chunks")
        self.manifest_path = self.chunks_dir / "manifest.json"
        
    def setup(self):
        """Create necessary directories."""
        os.makedirs(self.chunks_dir, exist_ok=True)
        
    def get_video_duration(self, video_path):
        """Get the duration of a video in seconds using ffprobe."""
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
            return None
            
    def needs_chunking(self, video_path, threshold=3600):
        """Determine if video needs chunking (longer than threshold)."""
        duration = self.get_video_duration(video_path)
        return duration > threshold  # 3600 seconds = 60 minutes
        
    def split_video(self, video_path):
        """
        Split video into chunks and create a manifest file.
        
        Returns:
            List of chunk paths if successful, None otherwise
        """
        try:
            video_filename = Path(video_path).stem
            duration = self.get_video_duration(video_path)
            
            if not duration:
                return None
                
            # Calculate chunk start times
            chunk_starts = []
            start_time = 0
            
            while start_time < duration:
                chunk_starts.append(start_time)
                start_time += self.chunk_size - self.overlap
                
            # Create chunks
            chunk_paths = []
            manifest = {
                "original_video": video_path,
                "duration": duration,
                "chunk_size": self.chunk_size,
                "overlap": self.overlap,
                "chunks": []
            }
            
            for i, start_time in enumerate(chunk_starts):
                # Calculate end time (either chunk_size or end of video)
                end_time = min(start_time + self.chunk_size, duration)
                
                # Output path for this chunk
                chunk_path = str(self.chunks_dir / f"{video_filename}_chunk_{i:03d}.mp4")
                
                # Use ffmpeg to extract the chunk
                try:
                    input_stream = ffmpeg.input(video_path, ss=start_time, t=end_time-start_time)
                    output = ffmpeg.output(input_stream, chunk_path, c="copy")
                    ffmpeg.run(output, overwrite_output=True, quiet=True)
                    
                    chunk_paths.append(chunk_path)
                    
                    # Add to manifest
                    manifest["chunks"].append({
                        "index": i,
                        "path": chunk_path,
                        "start_time": start_time,
                        "end_time": end_time,
                        "processed": False
                    })
                    
                    logger.info(f"Created chunk {i+1}/{len(chunk_starts)}: {start_time} to {end_time}")
                except Exception as e:
                    logger.error(f"Error creating chunk {i}: {e}")
                    return None
            
            # Save manifest
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
                
            return chunk_paths
                
        except Exception as e:
            logger.error(f"Error splitting video: {e}")
            return None
            
    def get_chunks(self):
        """Get all chunks from the manifest."""
        if not self.manifest_path.exists():
            return []
            
        with open(self.manifest_path, 'r') as f:
            manifest = json.load(f)
            
        return manifest["chunks"]
        
    def mark_chunk_processed(self, chunk_index):
        """Mark a chunk as processed in the manifest."""
        if not self.manifest_path.exists():
            return False
            
        with open(self.manifest_path, 'r') as f:
            manifest = json.load(f)
            
        for chunk in manifest["chunks"]:
            if chunk["index"] == chunk_index:
                chunk["processed"] = True
                break
                
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        return True
        
    def adjust_timestamp(self, timestamp, chunk_start_time):
        """Adjust a timestamp from a chunk to match the original video timeline."""
        # Parse timestamp format HH:MM:SS,mmm
        h, m, s = timestamp.split(':')
        s, ms = s.split(',')
        
        # Convert to seconds
        time_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        
        # Add chunk start time
        adjusted_time_seconds = time_seconds + chunk_start_time
        
        # Convert back to timestamp format
        adj_h = int(adjusted_time_seconds // 3600)
        adj_m = int((adjusted_time_seconds % 3600) // 60)
        adj_s = int(adjusted_time_seconds % 60)
        adj_ms = int((adjusted_time_seconds - int(adjusted_time_seconds)) * 1000)
        
        return f"{adj_h:02d}:{adj_m:02d}:{adj_s:02d},{adj_ms:03d}"
        
    def adjust_subtitle_timestamps(self, srt_content, chunk_start_time):
        """Adjust all timestamps in an SRT file to match the original video timeline."""
        import re
        
        # Find timestamp patterns in SRT content
        timestamp_pattern = r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})'
        
        def replace_timestamps(match):
            start_time = match.group(1)
            end_time = match.group(2)
            
            adjusted_start = self.adjust_timestamp(start_time, chunk_start_time)
            adjusted_end = self.adjust_timestamp(end_time, chunk_start_time)
            
            return f"{adjusted_start} --> {adjusted_end}"
            
        adjusted_content = re.sub(timestamp_pattern, replace_timestamps, srt_content)
        return adjusted_content 