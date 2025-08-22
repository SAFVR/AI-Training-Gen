import asyncio
import os
import sys
import logging
from loguru import logger

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the services
from app.services.azure_ai_service import azure_ai_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_azure_ai_base64.log')
    ]
)

# Configure loguru logger
logger.add("test_azure_ai_base64_detailed.log", level="DEBUG")

async def test_azure_ai_image_generation():
    """Test Azure AI image generation with base64 handling"""
    try:
        # Create a test prompt
        prompt = "A construction worker wearing a hard hat and safety vest, standing on a construction site with machinery in the background, bright daylight"
        
        # Create a temporary output directory
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_test_images")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate an image
        output_path = os.path.join(output_dir, "test_azure_ai_image.png")
        logger.info(f"Generating image with prompt: {prompt[:50]}...")
        
        result = await azure_ai_service.generate_image(prompt, output_path)
        
        # Check if the image was generated successfully
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"Image generated successfully at {output_path}")
            logger.info(f"Image file size: {file_size} bytes")
            
            if file_size > 0:
                logger.info("Test passed: Image file is not empty")
            else:
                logger.error("Test failed: Image file is empty")
        else:
            logger.error(f"Test failed: Image file was not created at {output_path}")
        
        return result
    except Exception as e:
        logger.error(f"Error in test_azure_ai_image_generation: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

async def main():
    try:
        # Test Azure AI image generation
        await test_azure_ai_image_generation()
        
        logger.info("All tests completed")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())