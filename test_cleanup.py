import asyncio
import os
import tempfile
import shutil
from loguru import logger
from app.services.video_generation_service import video_generation_service

async def test_cleanup():
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp(prefix="test_cleanup_")
        logger.info(f"Created temporary directory: {temp_dir}")
        
        # Create some test files in the temporary directory
        for i in range(3):
            with open(os.path.join(temp_dir, f"test_file_{i}.txt"), "w") as f:
                f.write(f"Test content {i}")
        
        logger.info(f"Created test files in {temp_dir}")
        
        # Test the cleanup function
        video_generation_service._cleanup_temp_files(temp_dir)
        
        # Check if the directory was removed
        if not os.path.exists(temp_dir):
            logger.info("Cleanup successful: temporary directory was removed")
        else:
            logger.error("Cleanup failed: temporary directory still exists")
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_cleanup())