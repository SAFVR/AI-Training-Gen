import asyncio
import json
from app.services.litellm_service import litellm_service
from app.services.video_generation_service import video_generation_service
from app.models.schemas import VideoGenerationRequest, VideoType
from loguru import logger

async def test_segmentation():
    # Test data
    job_data = {
        'job_title': 'Test Job',
        'job_description': 'Test Description',
        'location': 'Test Location',
        'equipment_used': 'Test Equipment',
        'industry_sector': 'Test Industry'
    }
    
    course_outline = {
        'title': 'Test Course',
        'description': 'Test Course Description',
        'sections': ['Section 1', 'Section 2']
    }
    
    # Test video segmentation
    try:
        segmentation = await litellm_service.generate_video_segmentation(job_data, course_outline)
        print("\nSegmentation result type:", type(segmentation))
        print("Segmentation result:", json.dumps(segmentation, indent=2))
        
        # Test clip prompts generation
        clip_prompts = await litellm_service.generate_video_clip_prompts(job_data, segmentation, "video")
        print("\nClip prompts result type:", type(clip_prompts))
        print("Clip prompts result:", json.dumps(clip_prompts, indent=2))
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        print(f"Error: {str(e)}")

async def test_video_generation():
    # Create a test request
    request = VideoGenerationRequest(
        job_title="Test Job",
        job_description="Test Description",
        location="Test Location",
        equipment_used="Test Equipment",
        industry_sector="Test Industry",
        video_type=VideoType.VIDEO
    )
    
    try:
        # Call the video generation service
        response = await video_generation_service.generate_video(request)
        print("\nVideo generation response:", response)
    except Exception as e:
        logger.error(f"Error in video generation test: {str(e)}")
        print(f"Error in video generation: {str(e)}")
        # Print the traceback for more details
        import traceback
        traceback.print_exc()

# Run the tests
async def main():
    print("Testing LiteLLM service...")
    await test_segmentation()
    print("\nTesting video generation service...")
    await test_video_generation()

if __name__ == "__main__":
    asyncio.run(main())