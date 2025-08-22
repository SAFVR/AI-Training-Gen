import asyncio
import logging
import os
import sys
import json
from typing import Dict, Any

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the services
from app.services.litellm_service import litellm_service
from app.models.schemas import VideoType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_litellm_service.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_video_segmentation():
    """Test the video segmentation function with minimal job data"""
    try:
        # Create minimal job data
        job_data = {
            "job_title": "Safety Training for Construction Workers",
            "job_description": "Basic safety training for construction site workers"
            # Intentionally missing fields to test error handling
        }
        
        # Create minimal course outline
        course_outline = {
            "title": "Construction Site Safety",
            "description": "Learn essential safety practices for construction sites",
            "sections": [
                "Introduction to Site Safety",
                "Personal Protective Equipment",
                "Hazard Identification"
            ]
        }
        
        logger.info("Testing generate_video_segmentation with minimal job data")
        segments = await litellm_service.generate_video_segmentation(job_data, course_outline)
        
        logger.info(f"Successfully generated {len(segments)} segments")
        logger.info(f"First segment: {json.dumps(segments[0], indent=2)}")
        
        return segments
    except Exception as e:
        logger.error(f"Error in test_video_segmentation: {str(e)}")
        raise

async def test_video_clip_prompts(segments):
    """Test the video clip prompts function with minimal job data"""
    try:
        # Create minimal job data
        job_data = {
            "job_title": "Safety Training for Construction Workers",
            "job_description": "Basic safety training for construction site workers"
            # Intentionally missing fields to test error handling
        }
        
        logger.info("Testing generate_video_clip_prompts with minimal job data")
        clip_prompts = await litellm_service.generate_video_clip_prompts(job_data, segments, VideoType.IMAGE)
        
        logger.info(f"Successfully generated {len(clip_prompts)} clip prompts")
        logger.info(f"First clip prompt: {json.dumps(clip_prompts[0], indent=2)}")
        
        return clip_prompts
    except Exception as e:
        logger.error(f"Error in test_video_clip_prompts: {str(e)}")
        raise

async def main():
    try:
        # Test video segmentation
        segments = await test_video_segmentation()
        
        # Test video clip prompts
        clip_prompts = await test_video_clip_prompts(segments)
        
        logger.info("All tests completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())