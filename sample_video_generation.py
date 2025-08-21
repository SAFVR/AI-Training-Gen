import os
import asyncio
import json
from dotenv import load_dotenv
from loguru import logger

from app.models.schemas import VideoGenerationRequest, VideoType
from app.services.video_generation_service import video_generation_service

# Load environment variables from .env file
load_dotenv()

async def generate_sample_video():
    """Generate a sample training video with S3 upload and Creatomate processing"""
    try:
        # Create a sample video generation request
        request = VideoGenerationRequest(
            job_title="Warehouse Safety Training",
            job_description="A comprehensive safety training video for warehouse workers covering forklift operation, "
                             "proper lifting techniques, hazard identification, and emergency procedures.",
            location="Warehouse Distribution Center",
            equipment_used="Forklifts, Pallet Jacks, Conveyor Belts, Personal Protective Equipment",
            industry_sector="Logistics and Distribution",
            video_type=VideoType.IMAGE  # Using IMAGE for faster generation
        )
        
        logger.info(f"Starting sample video generation for: {request.job_title}")
        
        # Generate the video
        response = await video_generation_service.generate_video(request)
        
        # Log the response
        logger.info("Video generation completed successfully!")
        logger.info(f"Local video URL: {response.video_url}")
        logger.info(f"S3 video URL: {response.s3_video_url}")
        logger.info(f"Creatomate video URL: {response.creatomate_video_url}")
        logger.info(f"Duration: {response.duration} seconds")
        logger.info(f"Clip count: {response.clip_count}")
        
        return response
    except Exception as e:
        logger.error(f"Error in sample video generation: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(generate_sample_video())