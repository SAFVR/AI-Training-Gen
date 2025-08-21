import asyncio
import os
import sys
from loguru import logger

from app.services.media_merge_service import media_merge_service

async def test_media_merge():
    # Set up logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # Check if ffmpeg is available
    if not await media_merge_service.check_ffmpeg_availability():
        logger.error("ffmpeg is not available. Please install ffmpeg or check the path.")
        return
    
    # Get sample video and audio files from the temp directory
    temp_dir = None
    for root, dirs, files in os.walk("temp"):
        if files and any(file.endswith(".mp4") for file in files) and any(file.endswith(".mp3") for file in files):
            temp_dir = root
            break
    
    if not temp_dir:
        logger.error("No sample files found in temp directory. Please run video generation first.")
        return
    
    # Get video and audio files
    video_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith(".mp4")]
    audio_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith(".mp3")]
    
    # Sort files to ensure they're in the correct order
    video_files = sorted(video_files, key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
    audio_files = sorted(audio_files, key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
    
    # Create sample subtitles
    subtitles = [f"Test subtitle {i+1}" for i in range(len(video_files))]
    
    # Create subtitle files
    subtitle_files = []
    for i, subtitle in enumerate(subtitles):
        subtitle_file = os.path.join(temp_dir, f"test_subtitle_{i+1}.srt")
        with open(subtitle_file, "w", encoding="utf-8") as f:
            f.write(f"1\n00:00:00,000 --> 00:00:10,000\n{subtitle}\n")
        subtitle_files.append(subtitle_file)
    
    # Create output directory
    os.makedirs("test_output", exist_ok=True)
    
    # Test merging
    try:
        output_path = "test_output/test_merged_video.mp4"
        logger.info(f"Testing media merge with {len(video_files)} clips")
        
        # Merge media
        result = await media_merge_service.merge_media(
            video_files,
            audio_files,
            subtitles,
            output_path
        )
        
        logger.info(f"Media merge test completed successfully: {result}")
        logger.info(f"Output file: {os.path.abspath(output_path)}")
    except Exception as e:
        logger.error(f"Media merge test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_media_merge())