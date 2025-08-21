import os
import asyncio
import logging
from dotenv import load_dotenv
from loguru import logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger.add("s3_creatomate_test.log", rotation="10 MB")

# Load environment variables
load_dotenv()

# Import services after loading environment variables
from app.services.s3_service import s3_service
from app.services.creatomate_service import creatomate_service

async def test_s3_creatomate_integration():
    try:
        # Test video path (replace with your actual video path)
        video_path = "video/Chemical_plant_Operator_20250821_173642.mp4"
        
        # Check if file exists
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return
        
        # Get file size for logging
        file_size = os.path.getsize(video_path)
        logger.info(f"Testing with video file: {video_path}")
        logger.info(f"File size: {file_size / (1024 * 1024):.2f} MB")
        
        # Check S3 configuration
        if not s3_service.s3_client or not s3_service.bucket_name:
            logger.warning("S3 not configured, will use direct Creatomate upload")
        else:
            logger.info(f"S3 configured with bucket: {s3_service.bucket_name}")
        
        # Process video with Creatomate template
        logger.info("Processing video with Creatomate template...")
        processed_video_path = await creatomate_service.process_video_with_template(video_path)
        
        logger.info(f"Video processing completed successfully!")
        logger.info(f"Processed video saved to: {processed_video_path}")
        
    except Exception as e:
        logger.error(f"Error in S3-Creatomate integration test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_s3_creatomate_integration())