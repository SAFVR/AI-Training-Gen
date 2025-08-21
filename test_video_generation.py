import httpx
import asyncio
import json
from loguru import logger

async def test_video_generation():
    url = "http://localhost:8000/api/generate_video"
    
    # Create a sample request payload
    payload = {
        "job_title": "Chemical Plant Operator",
        "job_description": "Operates and monitors chemical processing equipment in an industrial plant",
        "location": "Chemical manufacturing facility",
        "equipment_used": "Control systems, reactors, pumps, valves, monitoring equipment",
        "industry_sector": "Chemical Manufacturing",
        "video_type": "image"
    }
    
    try:
        logger.info(f"Sending video generation request to: {url}")
        async with httpx.AsyncClient(timeout=600.0) as client:  # Increased timeout for longer processing
            response = await client.post(url, json=payload)
            
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Video generation completed successfully!")
                logger.info(f"Local video URL: {result.get('video_url')}")
                logger.info(f"S3 video URL: {result.get('s3_video_url')}")
                logger.info(f"Creatomate video URL: {result.get('creatomate_video_url')}")
                logger.info(f"Duration: {result.get('duration')} seconds")
                logger.info(f"Clip count: {result.get('clip_count')}")
            else:
                logger.error(f"Error response: {response.text}")
            
    except Exception as e:
        logger.error(f"Error in video generation test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_video_generation())