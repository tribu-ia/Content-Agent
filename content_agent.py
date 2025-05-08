import argparse
from moviepy import * # Simple and nice, the __all__ is set in moviepy so only useful things will be loaded
def split_video(video_path:str, chunk_size:int = 30 , overlap:int = 20, video_chunk_prefix:str = None):
    """
    Splits the video into chunks of specified size with optional overlap.
    
    Args:
        video_path (str): Path to the video file.
        chunk_size (int): Size of each chunk in seconds.
        overlap (int): Overlap duration in seconds.
    """

    if video_chunk_prefix is None:
        video_file_name = video_path.split('/')[-1]
        video_file_name = video_file_name.split('.')[0]
        video_chunk_prefix = "data/"+video_file_name + '_chunk_'
    # Placeholder for video splitting logic
    print(f"Splitting video: {video_path}")
    print(f"Chunk size: {chunk_size} seconds")
    print(f"Overlap: {overlap} seconds")

    # Load the video file
    video = VideoFileClip(video_path)
    print("video",type(video),video)
    # Calculate the number of chunks
    total_duration = int(video.duration)
    print(f"Total duration: {total_duration} seconds")
    
    num_chunks = int(total_duration // chunk_size)
    # Create chunks with overlap
    for i in range(num_chunks):
        start_time = i * chunk_size - (overlap if i > 0 else 0)
        end_time = start_time + chunk_size
        if end_time > total_duration:
            break
        # Extract the chunk
        video_chunk = video.subclipped(start_time, end_time)
        # Save the chunk
        video_chunk.write_videofile(f"{video_chunk_prefix}{i}.mp4", codec="libx264")
    # Close the video file  
    video.close()




def main():
    parser = argparse.ArgumentParser(description='Video Splitter')
    parser.add_argument('-split_video', type=str, help='Path to the video file')
    parser.add_argument('-chunk_size', type=int, help='Chunk size in seconds',default=29*60)
    parser.add_argument('-overlap', type=int, help='Overlap duration in seconds',default=30)
    parser.add_argument('-video_chunk_prefix', type=str, help='Prefix for video chunks',default=None)
    args = parser.parse_args()

    # Access the parsed arguments
    video_path = args.split_video
    chunk_size = args.chunk_size
    overlap = args.overlap
    video_chunk_prefix = args.video_chunk_prefix
    split_video(video_path, chunk_size, overlap, video_chunk_prefix)

    

if __name__ == '__main__':
    main()


