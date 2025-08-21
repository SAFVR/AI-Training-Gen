import os
import uuid
import datetime
import shutil
from typing import Dict, Any, List, Optional
from loguru import logger

from app.models.schemas import VideoGenerationRequest, VideoGenerationResponse, VideoType
from app.services.litellm_service import litellm_service
from app.services.bytepulse_service import bytepulse_service
from app.services.elevenlabs_service import elevenlabs_service
from app.services.azure_ai_service import azure_ai_service
from app.services.media_merge_service import media_merge_service
from app.services.creatomate_service import creatomate_service
from app.services.s3_service import s3_service

class VideoGenerationService:
    async def generate_video(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        """Generate a training video based on the request"""
        try:
            # Create a unique ID for this video generation job
            job_id = str(uuid.uuid4())
            
            # Create directories for temporary files
            temp_dir = f"temp/{job_id}"
            os.makedirs(temp_dir, exist_ok=True)
            os.makedirs("video", exist_ok=True)
            
            # Convert request to dict for easier handling
            job_data = request.model_dump()
            
            # Step 1: Perform risk analysis
            logger.info(f"Performing risk analysis for job: {request.job_title}")
            risk_analysis = await litellm_service.generate_risk_analysis(job_data)
            
            # Step 2: Generate course outline
            logger.info(f"Generating course outline for job: {request.job_title}")
            course_outline = await litellm_service.generate_course_outline(job_data, risk_analysis)
            
            # Step 3: Generate video segmentation
            logger.info(f"Generating video segmentation for course: {course_outline['title']}")
            segmentation = await litellm_service.generate_video_segmentation(job_data, course_outline)
            
            # Step 4: Generate video clip prompts
            logger.info(f"Generating video clip prompts for {len(segmentation)} segments")
            # Ensure segmentation is a list of dictionaries with description field
            for i in range(len(segmentation)):
                if not isinstance(segmentation[i], dict):
                    segmentation[i] = {"description": str(segmentation[i])}
                elif "description" not in segmentation[i]:
                    segmentation[i]["description"] = f"Segment {i+1}"
            
            clip_prompts = await litellm_service.generate_video_clip_prompts(job_data, segmentation, request.video_type)
            
            # Step 5: Generate media based on video_type
            video_paths = []
            audio_paths = []
            subtitles = []
            
            for i, clip in enumerate(clip_prompts):
                # Generate video or image
                if request.video_type == VideoType.VIDEO:
                    logger.info(f"Generating video for clip {i+1}/18")
                    video_path = f"{temp_dir}/video_{i+1}.mp4"
                    await bytepulse_service.generate_video(clip["video_prompt"], video_path)
                else:  # IMAGE
                    logger.info(f"Generating image for clip {i+1}/18")
                    video_path = f"{temp_dir}/image_{i+1}.png"
                    await azure_ai_service.generate_image(clip["video_prompt"], video_path)
                
                # Generate audio narration
                logger.info(f"Generating audio for clip {i+1}/18")
                audio_path = f"{temp_dir}/audio_{i+1}.mp3"
                await elevenlabs_service.generate_audio(clip["audio_prompt"], audio_path)
                
                # Store paths and subtitle
                video_paths.append(video_path)
                audio_paths.append(audio_path)
                
                # Ensure subtitle_text is present and not empty
                subtitle_text = clip.get("subtitle_text", f"Safety information for segment {i+1}")
                if not subtitle_text or subtitle_text.strip() == "":
                    subtitle_text = f"Safety information for segment {i+1}"
                
                logger.info(f"Adding subtitle for clip {i+1}: {subtitle_text}")
                subtitles.append(subtitle_text)
            
            # Step 6: Merge media with ffmpeg
            logger.info("Merging media with ffmpeg")
            output_filename = f"{request.job_title.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            output_path = f"video/{output_filename}"
            final_video_path = await media_merge_service.merge_media(video_paths, audio_paths, subtitles, output_path)
            
            # Step 7: Upload merged video to S3
            logger.info("Uploading merged video to S3")
            s3_video_url = await s3_service.upload_file(final_video_path)
            if not s3_video_url:
                logger.warning("Failed to upload video to S3, continuing with local video path")
                s3_video_url = f"/video/{output_filename}"
            else:
                logger.info(f"Successfully uploaded video to S3: {s3_video_url}")
            
            # Step 8: Send to Creatomate for caption generation using S3 URL
            logger.info("Sending S3 video URL to Creatomate for caption generation")
            creatomate_video_url = None
            try:
                # Call Creatomate API to process the video with captions using the S3 URL
                creatomate_video_url = await creatomate_service.process_video_with_template(final_video_path, s3_video_url)
                logger.info(f"Successfully processed video with Creatomate: {creatomate_video_url}")
            except Exception as e:
                logger.error(f"Error processing video with Creatomate: {str(e)}")
                # Continue with the original video if Creatomate processing fails
                logger.info("Continuing with the original merged video")
            
            # Step 9: Clean up temporary files
            logger.info(f"Cleaning up temporary files in {temp_dir}")
            try:
                self._cleanup_temp_files(temp_dir)
                logger.info("Temporary files cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {str(e)}")
            
            # Step 10: Create response
            video_url = f"/video/{output_filename}"
            
            # Calculate approximate duration (10 seconds per clip)
            duration = len(clip_prompts) * 10.0
            
            response = VideoGenerationResponse(
                video_url=video_url,
                s3_video_url=s3_video_url,
                creatomate_video_url=creatomate_video_url,
                job_title=request.job_title,
                course_title=course_outline["title"],
                duration=duration,
                clip_count=len(clip_prompts),
                video_type=request.video_type,
                created_at=datetime.datetime.now().isoformat()
            )
            
            return response
        except Exception as e:
            error_message = str(e)
            # Ensure we have a meaningful error message
            if not error_message or error_message == "0":
                error_message = "Unknown error occurred during video generation"
            logger.error(f"Error generating video: {error_message}")
            raise Exception(error_message)

    # The _send_to_creatomate method has been removed as we now directly call creatomate_service in the main workflow
    
    def _cleanup_temp_files(self, temp_dir: str) -> None:
        """Clean up temporary files after video generation"""
        try:
            if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                logger.info(f"Cleaning up temporary files in {temp_dir}")
                shutil.rmtree(temp_dir)
                logger.info(f"Successfully removed temporary directory: {temp_dir}")
            else:
                logger.warning(f"Temporary directory not found: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")
            # Don't raise the exception, just log it

# Create a singleton instance
video_generation_service = VideoGenerationService()