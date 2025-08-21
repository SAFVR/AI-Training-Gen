from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from loguru import logger
from typing import Optional
import datetime

from app.models.schemas import VideoGenerationRequest, VideoGenerationResponse, VideoUploadRequest, VideoUploadResponse
from app.services.video_generation_service import video_generation_service
from app.services.s3_service import s3_service
from app.services.creatomate_service import creatomate_service

router = APIRouter()

@router.post("/generate_video", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """Generate a training video based on job details"""
    try:
        logger.info(f"Received video generation request for job: {request.job_title}")
        
        # Process the request and generate the video
        response = await video_generation_service.generate_video(request)
        
        logger.info(f"Video generation completed for job: {request.job_title}")
        return response
    except Exception as e:
        logger.error(f"Error processing video generation request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating video: {str(e)}")

@router.post("/caption_generator", response_model=VideoUploadResponse)
async def caption_generator(request: VideoUploadRequest):
    """Process a video from S3 URL with Creatomate for caption generation"""
    try:
        logger.info(f"Received caption generation request for video: {request.title}")
        logger.info(f"Processing S3 video URL: {request.video_url}")
        
        # Process with Creatomate using the provided S3 URL
        creatomate_video_url = await creatomate_service.process_video_with_template(None, request.video_url)
        if not creatomate_video_url:
            raise HTTPException(status_code=500, detail="Failed to process video with Creatomate")
        
        logger.info(f"Video processed by Creatomate: {creatomate_video_url}")
        
        # Create response
        response = VideoUploadResponse(
            original_video_url=request.video_url,
            creatomate_video_url=creatomate_video_url,
            title=request.title,
            description=request.description,
            created_at=datetime.datetime.now().isoformat()
        )
        
        return response
    except Exception as e:
        logger.error(f"Error processing video upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading video: {str(e)}")