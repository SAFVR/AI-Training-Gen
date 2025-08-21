from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from loguru import logger
from typing import Dict, Any

from app.models.schemas import VideoGenerationRequest, VideoGenerationResponse
from app.services.video_generation_service import video_generation_service

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