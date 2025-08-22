import os
import sys
import subprocess
from loguru import logger

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.media_merge_service import MediaMergeService

def test_subtitle_embedding():
    # Set up logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # Initialize the media merge service
    media_service = MediaMergeService()
    
    # Check if ffmpeg is available
    if not media_service.check_ffmpeg_availability():
        logger.error("FFmpeg is not available. Cannot run test.")
        return False
    
    # Create test directory
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_font_fix")
    os.makedirs(test_dir, exist_ok=True)
    
    # Create a simple SRT subtitle file
    subtitle_text = "This is a test subtitle with font"
    subtitle_file = os.path.join(test_dir, "test.srt")
    
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        f.write("1\n")
        f.write("00:00:00,000 --> 00:00:05,000\n")
        f.write(f"{subtitle_text}\n")
    
    # Create a test video if it doesn't exist
    test_video = os.path.join(test_dir, "test.mp4")
    if not os.path.exists(test_video):
        logger.info("Creating test video...")
        # Create a 5-second blue test video
        cmd = [
            media_service.ffmpeg_path,
            '-f', 'lavfi',
            '-i', 'color=c=blue:s=1280x720:d=5',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',
            test_video
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Output path for the video with subtitles
    output_path = os.path.join(test_dir, "test_with_subtitles.mp4")
    
    # Call the _merge_video_subtitle_only method directly
    try:
        # Use asyncio to run the async method
        import asyncio
        asyncio.run(media_service._merge_video_subtitle_only(test_video, subtitle_file, output_path))
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"✓ Subtitle embedding test passed! Output file: {os.path.abspath(output_path)}")
            return True
        else:
            logger.error("✗ Subtitle embedding test failed: Output file not created or empty")
            return False
    except Exception as e:
        logger.error(f"✗ Subtitle embedding test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    test_subtitle_embedding()