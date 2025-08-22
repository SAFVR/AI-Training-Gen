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
                # Generate video or image
                video_path = ""
                skip_current_clip = False
                try:
                    if request.video_type == VideoType.VIDEO:
                        logger.info(f"Generating video for clip {i+1}/{len(clip_prompts)}")
                        video_path = f"{temp_dir}/video_{i+1}.mp4"
                        # Validate video prompt
                        if not clip.get("video_prompt") or clip["video_prompt"].strip() == "":
                            logger.warning(f"Empty video prompt detected for clip {i+1}, skipping this clip")
                            skip_current_clip = True
                        else:
                            try:
                                await bytepulse_service.generate_video(clip["video_prompt"], video_path)
                            except Exception as video_error:
                                logger.error(f"Error generating video for clip {i+1}: {str(video_error)}")
                                # Skip this clip and continue with the next one
                                skip_current_clip = True
                    else:  # IMAGE
                        logger.info(f"Generating image for clip {i+1}/{len(clip_prompts)}")
                        video_path = f"{temp_dir}/image_{i+1}.png"
                        # Ensure the video prompt is not empty
                        if not clip.get("video_prompt") or clip["video_prompt"].strip() == "":
                            logger.warning(f"Empty image prompt detected for clip {i+1}, skipping this clip")
                            skip_current_clip = True
                        else:
                            # Try to generate the image with the original prompt
                            try:
                                await azure_ai_service.generate_image(clip["video_prompt"], video_path)
                            except Exception as img_error:
                                logger.warning(f"First attempt at image generation for clip {i+1} failed: {str(img_error)}")
                                
                                # Check if it's a content violation error
                                error_str = str(img_error).lower()
                                if "content rejected" in error_str or "violence detection" in error_str or "content filter" in error_str:
                                    logger.info(f"Content violation detected for clip {i+1}, trying alternative prompt")
                                    
                                    # Create a more neutral version of the prompt
                                    original_prompt = clip["video_prompt"]
                                    safe_prompt = f"A safe workplace training image showing {original_prompt.split('showing')[-1] if 'showing' in original_prompt else 'proper safety procedures'}"
                                    
                                    # Try with the safer prompt
                                    try:
                                        logger.info(f"Attempting with alternative prompt for clip {i+1}: {safe_prompt}")
                                        await azure_ai_service.generate_image(safe_prompt, video_path)
                                    except Exception as safe_error:
                                        logger.warning(f"Alternative prompt also failed for clip {i+1}: {str(safe_error)}")
                                        
                                        # Try with an even more generic safety prompt
                                        generic_prompt = f"A professional workplace safety training image with neutral content"
                                        try:
                                            logger.info(f"Attempting with generic safety prompt for clip {i+1}")
                                            await azure_ai_service.generate_image(generic_prompt, video_path)
                                        except Exception as generic_error:
                                            logger.error(f"All image generation attempts failed for clip {i+1}, skipping this clip")
                                            skip_current_clip = True
                                else:
                                    # If it's not a content violation, try a generic safety image
                                    generic_prompt = f"A professional workplace safety training image with neutral content"
                                    try:
                                        logger.info(f"Attempting with generic safety prompt for clip {i+1}")
                                        await azure_ai_service.generate_image(generic_prompt, video_path)
                                    except Exception as generic_error:
                                        logger.error(f"All image generation attempts failed for clip {i+1}, skipping this clip")
                                        skip_current_clip = True
                except Exception as e:
                    logger.error(f"Unexpected error generating {'video' if request.video_type == VideoType.VIDEO else 'image'} for clip {i+1}: {str(e)}")
                    skip_current_clip = True
                
                # If we couldn't generate video/image, skip this clip
                if skip_current_clip:
                    logger.warning(f"Skipping clip {i+1} due to video/image generation failure")
                    continue
                
                # Generate audio narration
                audio_path = ""
                audio_generation_failed = False
                try:
                    logger.info(f"Generating audio for clip {i+1}/{len(clip_prompts)}")
                    audio_path = f"{temp_dir}/audio_{i+1}.mp3"
                    # Validate audio prompt
                    if not clip.get("audio_prompt") or clip["audio_prompt"].strip() == "":
                        logger.warning(f"Empty audio prompt detected for clip {i+1}, using generic audio")
                        clip["audio_prompt"] = f"Safety information for segment {i+1}"
                    
                    # Try to generate audio with the original prompt
                    try:
                        await elevenlabs_service.generate_audio(clip["audio_prompt"], audio_path)
                    except Exception as audio_error:
                        logger.warning(f"First attempt at audio generation for clip {i+1} failed: {str(audio_error)}")
                        
                        # Create a more neutral version of the prompt
                        original_prompt = clip["audio_prompt"]
                        safe_prompt = f"Safety information: {original_prompt.split(':', 1)[1] if ':' in original_prompt else original_prompt}"
                        
                        # Try with the safer prompt
                        try:
                            logger.info(f"Attempting with alternative audio prompt for clip {i+1}")
                            await elevenlabs_service.generate_audio(safe_prompt, audio_path)
                        except Exception as safe_error:
                            logger.warning(f"Alternative audio prompt also failed for clip {i+1}: {str(safe_error)}")
                            
                            # Try with an even more generic safety prompt
                            generic_prompt = f"This is important workplace safety information that should be followed carefully."
                            try:
                                logger.info(f"Attempting with generic audio prompt for clip {i+1}")
                                await elevenlabs_service.generate_audio(generic_prompt, audio_path)
                            except Exception as generic_error:
                                logger.error(f"All audio generation attempts failed for clip {i+1}")
                                audio_generation_failed = True
                except Exception as e:
                    logger.error(f"Unexpected error generating audio for clip {i+1}: {str(e)}")
                    audio_generation_failed = True
                
                # If audio generation failed, we can still use the video/image without audio
                if audio_generation_failed:
                    logger.warning(f"Audio generation failed for clip {i+1}, continuing without audio")
                    # Create an empty audio file or skip this clip if audio is essential
                    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                        # Create a silent audio file
                        audio_path = f"{temp_dir}/silent_audio_{i+1}.mp3"
                        # We'll handle this in the merge step
                    else:
                        # If both video and audio failed, skip this clip
                        logger.warning(f"Both video and audio failed for clip {i+1}, skipping this clip")
                        continue
                
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
            try:
                final_video_path = await media_merge_service.merge_media(video_paths, audio_paths, subtitles, output_path)
                if not os.path.exists(final_video_path):
                    raise Exception(f"Media merge completed but output file not found at {final_video_path}")
            except Exception as e:
                logger.error(f"Error merging media: {str(e)}")
                raise Exception(f"Failed to merge media files: {str(e)}")
            
            # Step 7: Upload merged video to S3
            logger.info("Uploading merged video to S3")
            try:
                s3_video_url = await s3_service.upload_file(final_video_path)
                if not s3_video_url:
                    logger.warning("Failed to upload video to S3, continuing with local video path")
                    s3_video_url = f"/video/{output_filename}"
                else:
                    logger.info(f"Successfully uploaded video to S3: {s3_video_url}")
            except Exception as e:
                logger.error(f"Error uploading to S3: {str(e)}")
                # Fall back to local path but continue execution
                s3_video_url = f"/video/{output_filename}"
                logger.warning(f"Using local video path due to S3 upload failure: {s3_video_url}")
            
            # Step 8: Send to Creatomate for caption generation using S3 URL
            logger.info("Sending S3 video URL to Creatomate for caption generation")
            creatomate_video_url = None
            try:
                # Call Creatomate API to process the video with captions using the S3 URL
                creatomate_video_url = await creatomate_service.process_video_with_template(final_video_path, s3_video_url)
                if not creatomate_video_url:
                    raise Exception("Creatomate returned empty URL")
                logger.info(f"Successfully processed video with Creatomate: {creatomate_video_url}")
            except Exception as e:
                logger.error(f"Error processing video with Creatomate: {str(e)}")
                # Continue with the original video if Creatomate processing fails
                logger.warning("Continuing with the original merged video due to Creatomate processing failure")
            
            # Step 9: Clean up temporary files
            logger.info(f"Cleaning up temporary files in {temp_dir}")
            try:
                self._cleanup_temp_files(temp_dir)
                logger.info("Temporary files cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {str(e)}")
                # Continue execution even if cleanup fails
                logger.warning("Continuing despite cleanup failure")
            
            # Step 10: Create response
            video_url = f"/video/{output_filename}"
            
            # Calculate approximate duration (10 seconds per clip)
            duration = len(clip_prompts) * 10.0
            
            # Verify that required fields are available
            if not course_outline or not isinstance(course_outline, dict) or "title" not in course_outline:
                logger.warning("Course outline missing or invalid, using job title as course title")
                course_title = request.job_title
            else:
                course_title = course_outline["title"]
            
            # Ensure we have valid URLs
            if not os.path.exists(final_video_path):
                logger.error(f"Final video file not found at {final_video_path}")
                raise Exception("Video generation failed: Output file not found")
            
            # Ensure we have a valid Creatomate URL
            if creatomate_video_url:
                logger.info(f"Using Creatomate URL in response: {creatomate_video_url}")
            else:
                logger.warning("Creatomate URL is missing, falling back to S3 or local URL")
                
            # Create response without including Creatomate URL
            response = VideoGenerationResponse(
                video_url=video_url,
                s3_video_url=s3_video_url or video_url,  # Fallback to local URL if S3 failed
                creatomate_video_url=None,  # Explicitly set to None to remove from response
                job_title=request.job_title,
                course_title=course_title,
                duration=duration,
                clip_count=len(clip_prompts),
                video_type=request.video_type,
                created_at=datetime.datetime.now().isoformat()
            )
            
            logger.info("Creatomate URL removed from response as requested")
            
            return response
        except Exception as e:
            error_message = str(e)
            # Ensure we have a meaningful error message
            if not error_message or error_message == "0":
                error_message = "Unknown error occurred during video generation"
            
            # Add more detailed error information
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error generating video: {error_message}")
            logger.error(f"Error traceback: {error_traceback}")
            
            # Provide more specific error message based on where the error occurred
            if "litellm_service" in error_traceback:
                error_message = f"Error in AI text generation: {error_message}"
            elif "azure_ai_service" in error_traceback:
                error_message = f"Error in image generation: {error_message}"
            elif "bytepulse_service" in error_traceback:
                error_message = f"Error in video clip generation: {error_message}"
            elif "elevenlabs_service" in error_traceback:
                error_message = f"Error in audio generation: {error_message}"
            elif "media_merge_service" in error_traceback:
                error_message = f"Error in media merging: {error_message}"
            elif "s3_service" in error_traceback:
                error_message = f"Error in S3 upload: {error_message}"
            elif "creatomate_service" in error_traceback:
                error_message = f"Error in Creatomate processing: {error_message}"
            
            raise Exception(error_message)

    # The _send_to_creatomate method has been removed as we now directly call creatomate_service in the main workflow
    
    def _cleanup_temp_files(self, temp_dir: str) -> None:
        """Clean up temporary files after video generation"""
        if not temp_dir or not isinstance(temp_dir, str):
            logger.error(f"Invalid temp_dir provided for cleanup: {temp_dir}")
            return
            
        try:
            if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                logger.info(f"Cleaning up temporary files in {temp_dir}")
                # List files before deletion for debugging purposes
                try:
                    files = os.listdir(temp_dir)
                    logger.debug(f"Files to be deleted: {files}")
                except Exception as list_err:
                    logger.warning(f"Could not list files in {temp_dir}: {str(list_err)}")
                
                # Attempt to remove the directory
                shutil.rmtree(temp_dir)
                logger.info(f"Successfully removed temporary directory: {temp_dir}")
            else:
                logger.warning(f"Temporary directory not found or not a directory: {temp_dir}")
        except PermissionError as pe:
            logger.error(f"Permission error when cleaning up {temp_dir}: {str(pe)}")
            logger.warning("Some files may be in use by another process")
        except OSError as ose:
            logger.error(f"OS error when cleaning up {temp_dir}: {str(ose)}")
            # Try to remove files one by one
            try:
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for file in files:
                        try:
                            os.remove(os.path.join(root, file))
                        except Exception as file_err:
                            logger.warning(f"Could not remove file {file}: {str(file_err)}")
                logger.info("Attempted to clean up files individually")
            except Exception as walk_err:
                logger.error(f"Error during individual file cleanup: {str(walk_err)}")
        except Exception as e:
            logger.error(f"Unexpected error cleaning up temporary files: {str(e)}")
            # Don't raise the exception, just log it

# Create a singleton instance
video_generation_service = VideoGenerationService()