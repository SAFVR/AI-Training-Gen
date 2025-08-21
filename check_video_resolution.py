import os
import subprocess
import sys
from loguru import logger

from app.services.media_merge_service import media_merge_service

async def check_video_resolution():
    # Set up logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    video_path = "test_output/test_merged_video.mp4"
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return
    
    # Use the ffmpeg path from media_merge_service
    ffmpeg_path = media_merge_service.ffmpeg_path
    
    # Run ffmpeg to get video information
    cmd = [
        ffmpeg_path,
        "-i", video_path
    ]
    
    try:
        # ffmpeg outputs to stderr by default
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr
        
        # Look for video stream information
        for line in output.split('\n'):
            if 'Video:' in line:
                logger.info(f"Video info: {line.strip()}")
                
                # Look for resolution pattern like 1920x1080
                if "1920x1080" in line:
                    logger.info(f"✓ Resolution confirmed: 1920x1080 as requested")
                    break
    except Exception as e:
        logger.error(f"Error checking video resolution: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_video_resolution())