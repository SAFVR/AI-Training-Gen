from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form
from fastapi.responses import JSONResponse
from loguru import logger
from typing import Dict, Any, Optional
import os
import shutil
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

@router.post("/upload_video", response_model=VideoUploadResponse)
async def upload_video(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    video_file: UploadFile = File(...)
):
    """Upload a video to S3 and process it with Creatomate"""
    try:
        logger.info(f"Received video upload request: {title}")
        
        # Create video directory if it doesn't exist
        os.makedirs("video", exist_ok=True)
        
        # Save the uploaded file temporarily
        temp_file_path = f"video/{video_file.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        
        logger.info(f"Video saved temporarily at: {temp_file_path}")
        
        # Upload to S3
        s3_video_url = await s3_service.upload_file(temp_file_path)
        if not s3_video_url:
            raise HTTPException(status_code=500, detail="Failed to upload video to S3")
        
        logger.info(f"Video uploaded to S3: {s3_video_url}")
        
        # Process with Creatomate
        creatomate_video_url = await creatomate_service.process_video_with_template(temp_file_path, s3_video_url)
        if not creatomate_video_url:
            raise HTTPException(status_code=500, detail="Failed to process video with Creatomate")
        
        logger.info(f"Video processed by Creatomate: {creatomate_video_url}")
        
        # Create response
        response = VideoUploadResponse(
            original_video_url=s3_video_url,
            creatomate_video_url=creatomate_video_url,
            title=title,
            description=description,
            created_at=datetime.datetime.now().isoformat()
        )
        
        return response
    except Exception as e:
        logger.error(f"Error processing video upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading video: {str(e)}")