import os
import subprocess
import asyncio
import sys
import shutil
import urllib.request
import zipfile
from typing import List, Optional
from loguru import logger


class MediaMergeService:
    def __init__(self):
        # Try to find ffmpeg in the system PATH
        self.ffmpeg_path = self._find_ffmpeg()
        
        # Log ffmpeg availability
        logger.info(f"MediaMergeService initialized with ffmpeg path: {self.ffmpeg_path}")
        
        # Check if ffmpeg is working
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if result.returncode == 0:
                logger.info(f"ffmpeg is available: {result.stdout.splitlines()[0] if result.stdout else ''}")
            else:
                logger.warning(f"ffmpeg check failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"Error checking ffmpeg during initialization: {str(e)}")
            logger.warning("Media merging functionality may not work properly.")

        
    def _find_ffmpeg(self) -> str:
        """Find ffmpeg executable or download a portable version if not found"""
        # First check if ffmpeg is in PATH
        ffmpeg_command = "ffmpeg" if sys.platform != "win32" else "ffmpeg.exe"
        ffmpeg_path = shutil.which(ffmpeg_command)
        
        if ffmpeg_path:
            logger.info(f"Found ffmpeg in system PATH: {ffmpeg_path}")
            return ffmpeg_path
        
        # If not found, use a portable version in the app directory
        portable_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin")
        os.makedirs(portable_dir, exist_ok=True)
        
        portable_ffmpeg = os.path.join(portable_dir, ffmpeg_command)
        
        # Check if portable version already exists
        if os.path.exists(portable_ffmpeg):
            logger.info(f"Using portable ffmpeg: {portable_ffmpeg}")
            return portable_ffmpeg
        
        # Download portable ffmpeg
        logger.info("Downloading portable ffmpeg...")
        try:
            if sys.platform == "win32":
                # Windows version
                url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                zip_path = os.path.join(portable_dir, "ffmpeg.zip")
                
                # Download the zip file
                urllib.request.urlretrieve(url, zip_path)
                
                # Extract the zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(portable_dir)
                
                # Find the ffmpeg.exe in the extracted directory
                for root, dirs, files in os.walk(portable_dir):
                    if ffmpeg_command in files:
                        extracted_ffmpeg = os.path.join(root, ffmpeg_command)
                        # Move to the bin directory
                        shutil.copy(extracted_ffmpeg, portable_ffmpeg)
                        break
                
                # Clean up
                os.remove(zip_path)
                
                if os.path.exists(portable_ffmpeg):
                    logger.info(f"Successfully downloaded portable ffmpeg: {portable_ffmpeg}")
                    return portable_ffmpeg
            else:
                # For Linux/Mac, suggest installation
                logger.error("ffmpeg not found. Please install ffmpeg using your package manager.")
                logger.error("For Ubuntu/Debian: sudo apt-get install ffmpeg")
                logger.error("For macOS: brew install ffmpeg")
        except Exception as e:
            logger.error(f"Failed to download portable ffmpeg: {str(e)}")
        
        # If all else fails, return the command name and hope it works
        logger.warning(f"Could not find or download ffmpeg. Using '{ffmpeg_command}' and hoping it works.")
        return ffmpeg_command
        
    async def merge_media(self, video_paths: List[str], audio_paths: List[str], subtitles: List[str], output_path: str) -> str:
        """Merge video/image, audio, and subtitles using ffmpeg"""
        try:
            logger.info(f"Starting media merge process for {len(video_paths)} clips")
            
            # Create temporary directory for intermediate files
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            temp_dir = output_dir
            
            # Create a list to store paths of intermediate files with audio
            intermediate_files = []
            
            # Step 1: Add audio to each video clip and create subtitle files
            for i, (video_path, audio_path, subtitle) in enumerate(zip(video_paths, audio_paths, subtitles)):
                # Skip if video file doesn't exist or is empty
                if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                    logger.warning(f"Skipping clip {i+1}: Video file missing or empty at {video_path}")
                    continue
                
                # Create output path for intermediate file
                intermediate_file = f"{temp_dir}/temp_clip_{i+1}.mp4"
                
                # Check if audio file exists and is not empty
                has_audio = os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
                audio_duration = 10.0  # Default duration in seconds
                
                if has_audio:
                    # Get audio duration using ffmpeg
                    try:
                        audio_duration = await self._get_audio_duration(audio_path)
                        logger.info(f"Detected audio duration for clip {i+1}: {audio_duration} seconds")
                    except Exception as e:
                        logger.warning(f"Failed to get audio duration for clip {i+1}: {str(e)}. Using default 10 seconds.")
                else:
                    logger.warning(f"Audio file missing or empty for clip {i+1}, creating silent audio with default duration")
                    # Create a silent audio file with the default duration
                    silent_audio_path = f"{temp_dir}/silent_audio_{i+1}.mp3"
                    await self._create_silent_audio(silent_audio_path, audio_duration)  # Default seconds of silence
                    audio_path = silent_audio_path
                
                # Create subtitle file with the same duration as the audio
                subtitle_file = f"{temp_dir}/subtitle_{i+1}.srt"
                await self._create_subtitle_file(subtitle_file, subtitle, audio_duration)
                
                # Merge video and audio using ffmpeg
                try:
                    await self._merge_video_audio_subtitle(video_path, audio_path, subtitle_file, intermediate_file)
                    intermediate_files.append(intermediate_file)
                    logger.info(f"Created intermediate clip {i+1} with audio and subtitles")
                except Exception as e:
                    logger.error(f"Failed to merge clip {i+1}: {str(e)}")
                    # Try to create a clip with just the video and subtitles, no audio
                    try:
                        logger.info(f"Attempting to create clip {i+1} without audio")
                        await self._merge_video_subtitle_only(video_path, subtitle_file, intermediate_file)
                        intermediate_files.append(intermediate_file)
                        logger.info(f"Created intermediate clip {i+1} with subtitles only (no audio)")
                    except Exception as e2:
                        logger.error(f"Failed to create clip {i+1} even without audio: {str(e2)}")
                        # Skip this clip entirely
                        continue
            
            # Check if we have any intermediate files to concatenate
            if not intermediate_files:
                logger.error("No valid clips were created, cannot generate final video")
                raise Exception("No valid clips were created, cannot generate final video")
            
            # Step 2: Concatenate all intermediate files
            await self._concatenate_videos(intermediate_files, output_path)
            
            # Step 3: Clean up intermediate files
            for file in intermediate_files:
                if os.path.exists(file):
                    os.remove(file)
            
            logger.info(f"Media merge completed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error merging media: {str(e)}")
            raise Exception(f"Media merging failed: {str(e)}")
    
    async def _create_subtitle_file(self, subtitle_file: str, subtitle_text: str, duration_seconds: float = 10.0) -> None:
        """Create a simple SRT subtitle file with duration based on audio length"""
        try:
            logger.info(f"Creating subtitle file with text: {subtitle_text} and duration: {duration_seconds} seconds")
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                f.write("1\n")
                end_time = self._format_time(duration_seconds)
                f.write(f"00:00:00,000 --> {end_time}\n")
                f.write(f"{subtitle_text}\n")
            logger.info(f"Subtitle file created successfully: {subtitle_file}")
        except Exception as e:
            logger.error(f"Error creating subtitle file: {str(e)}")
            raise Exception(f"Failed to create subtitle file: {str(e)}")
            
    def _format_time(self, seconds: float) -> str:
        """Format seconds into SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds_remainder = seconds % 60
        whole_seconds = int(seconds_remainder)
        milliseconds = int((seconds_remainder - whole_seconds) * 1000)
        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get the duration of an audio file in seconds using ffmpeg"""
        try:
            # First check if the file exists and log detailed information
            logger.debug(f"Checking audio file existence: {audio_path}")
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                # Check if the directory exists
                dir_path = os.path.dirname(audio_path)
                if not os.path.exists(dir_path):
                    logger.error(f"Directory does not exist: {dir_path}")
                else:
                    # List files in the directory for debugging
                    try:
                        files = os.listdir(dir_path)
                        logger.debug(f"Files in directory {dir_path}: {files}")
                    except Exception as list_err:
                        logger.error(f"Error listing directory: {str(list_err)}")
                
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
                
            # Check if file is empty
            file_size = os.path.getsize(audio_path)
            logger.debug(f"Audio file size: {file_size} bytes")
            if file_size == 0:
                logger.error(f"Audio file is empty: {audio_path}")
                raise ValueError(f"Audio file is empty: {audio_path}")
                
            # Use ffprobe to get the duration of the audio file
            cmd = [
                self.ffmpeg_path.replace('ffmpeg', 'ffprobe'),  # Use ffprobe instead of ffmpeg
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            
            cmd_str = ' '.join(cmd)
            logger.debug(f"Running ffprobe command to get audio duration: {cmd_str}")
            
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if process.returncode != 0:
                logger.error(f"ffprobe error (code {process.returncode}): {process.stderr}")
                raise Exception(f"ffprobe error: {process.stderr}")
            
            # Parse the duration from the output
            output = process.stdout.strip()
            logger.debug(f"ffprobe raw output: '{output}'")
            if not output:
                logger.error("ffprobe returned empty output")
                raise ValueError("Could not determine audio duration: empty ffprobe output")
                
            try:
                duration = float(output)
                logger.debug(f"Detected audio duration: {duration} seconds")
                return duration
            except ValueError as ve:
                logger.error(f"Invalid duration value: '{output}'. Error: {str(ve)}")
                raise ValueError(f"Could not parse audio duration: {str(ve)}")
                
        except FileNotFoundError as e:
            logger.error(f"Audio file not found: {str(e)}")
            # Return default duration instead of raising exception
            logger.warning("Using default duration of 10 seconds")
            return 10.0
        except ValueError as e:
            logger.error(f"Invalid audio file: {str(e)}")
            # Return default duration instead of raising exception
            logger.warning("Using default duration of 10 seconds due to invalid audio file")
            return 10.0
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            # Return default duration instead of raising exception
            logger.warning("Using default duration of 10 seconds due to error")
            return 10.0
    
    async def _create_silent_audio(self, silent_audio_path: str, duration_seconds: float) -> None:
        """Create a silent audio file with specified duration"""
        try:
            # Create a silent audio file using ffmpeg
            cmd = [
                self.ffmpeg_path,
                '-f', 'lavfi',
                '-i', f"anullsrc=r=44100:cl=stereo",
                '-t', str(duration_seconds),
                '-c:a', 'libmp3lame',
                '-b:a', '128k',
                '-y',
                silent_audio_path
            ]
            
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if process.returncode != 0:
                logger.error(f"ffmpeg silent audio error: {process.stderr}")
                raise Exception(f"ffmpeg silent audio error: {process.stderr}")
                
            logger.info(f"Created silent audio file: {silent_audio_path}")
        except Exception as e:
            logger.error(f"Error creating silent audio: {str(e)}")
            raise Exception(f"Failed to create silent audio: {str(e)}")
            
    async def _merge_video_audio_subtitle(self, video_path: str, audio_path: str, subtitle_path: str, output_path: str) -> None:
        """Merge video, audio and subtitle into a single clip"""
        try:
            # Read subtitle text from file
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                subtitle_content = f.read()
                # Extract subtitle text (assuming SRT format with text on the third line)
                subtitle_lines = subtitle_content.split('\n')
                subtitle_text = subtitle_lines[2] if len(subtitle_lines) > 2 else ""
                
            logger.info(f"Merging video with subtitle text: {subtitle_text}")
            
            # Get audio duration for setting image duration if needed
            audio_duration = 10.0  # Default duration
            try:
                audio_duration = await self._get_audio_duration(audio_path)
                logger.info(f"Using audio duration for clip: {audio_duration} seconds")
            except Exception as e:
                logger.warning(f"Failed to get audio duration: {str(e)}. Using default 10 seconds.")
            
            # Check if input is an image (png, jpg, etc.) that needs to be converted to video
            is_image = os.path.splitext(video_path)[1].lower() in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
            
            # Create a temporary file for the video with hardcoded subtitles
            temp_video_path = f"{os.path.splitext(output_path)[0]}_temp{os.path.splitext(output_path)[1]}"
            
            if is_image:
                # Convert image to video with duration matching audio
                logger.info(f"Converting image to video with duration {audio_duration} seconds")
                image_to_video_cmd = [
                    self.ffmpeg_path,
                    '-loop', '1',  # Loop the image
                    '-i', video_path,  # Input image
                    '-c:v', 'libx264',  # Use H.264 codec
                    '-t', str(audio_duration),  # Set duration to match audio
                    '-pix_fmt', 'yuv420p',  # Required for compatibility
                    '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',  # Scale and pad to 1080p
                    '-y',  # Overwrite output
                    temp_video_path
                ]
                
                logger.info(f"Running image to video conversion")
                
                image_process = subprocess.run(
                    image_to_video_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if image_process.returncode != 0:
                    logger.error(f"ffmpeg image to video error: {image_process.stderr}")
                    raise Exception(f"ffmpeg image to video error: {image_process.stderr}")
                
                # Now use the generated video for further processing
                video_path = temp_video_path
                
            # Create a temporary file for the video with hardcoded subtitles
            subtitle_video_path = f"{os.path.splitext(output_path)[0]}_subtitle_temp{os.path.splitext(output_path)[1]}"
            
            # Add subtitles to the video and set resolution to 1920x1080 (standard HD)
            # Using Alignment=2 for top center positioning
            subtitle_cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-vf', f"subtitles='{subtitle_path.replace('\\', '/')}':force_style='FontSize=24,FontName=Arial,Alignment=2,BorderStyle=1,Outline=2,Shadow=0,MarginV=50,PrimaryColour=&HFFFFFF,OutlineColour=&H000000',scale=1920:1080",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-y',
                subtitle_video_path
            ]
            
            logger.info(f"Running subtitle embedding command")
            
            # Run ffmpeg command to add subtitles
            subtitle_process = subprocess.run(
                subtitle_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if subtitle_process.returncode != 0:
                logger.error(f"ffmpeg subtitle error: {subtitle_process.stderr}")
                # If subtitles fail, try an alternative approach with drawtext filter
                logger.warning("Subtitle embedding failed, trying alternative method")
                
                # Try with drawtext filter instead and set resolution to 1920x1080 (standard HD)
                # Position subtitles at the top center of the frame
                alt_subtitle_cmd = [
                    self.ffmpeg_path,
                    '-i', video_path,
                    '-vf', f"drawtext=text='{subtitle_text.replace("'", "\'").replace('"', '\"')}':fontcolor=white:fontsize=24:fontname=Arial:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=50,scale=1920:1080",
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-y',
                    subtitle_video_path
                ]
                
                logger.info(f"Running alternative subtitle embedding command with drawtext")
                
                alt_subtitle_process = subprocess.run(
                    alt_subtitle_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if alt_subtitle_process.returncode != 0:
                    logger.error(f"Alternative subtitle method failed: {alt_subtitle_process.stderr}")
                    logger.warning("All subtitle methods failed, continuing with video and audio only")
                    subtitle_video_path = video_path
            
            # Now merge the video with audio
            audio_cmd = [
                self.ffmpeg_path,
                '-i', subtitle_video_path,
                '-i', audio_path,
                '-c:v', 'copy',  # Copy video stream without re-encoding
                '-c:a', 'aac',   # Encode audio as AAC
                '-map', '0:v',   # Use video from first input
                '-map', '1:a',   # Use audio from second input
                '-shortest',      # Match duration to shortest input
                '-y',            # Overwrite output file if it exists
                output_path
            ]
            
            # Run ffmpeg command to add audio
            audio_process = subprocess.run(
                audio_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Clean up temporary files if they were created
            for temp_file in [temp_video_path, subtitle_video_path]:
                if temp_file != video_path and os.path.exists(temp_file):
                    os.remove(temp_file)
            
            if audio_process.returncode != 0:
                logger.error(f"ffmpeg audio error: {audio_process.stderr}")
                raise Exception(f"ffmpeg audio error: {audio_process.stderr}")
                
        except Exception as e:
            logger.error(f"Error merging video and audio: {str(e)}")
            raise Exception(f"Failed to merge video and audio: {str(e)}")
            
    async def _merge_video_subtitle_only(self, video_path: str, subtitle_path: str, output_path: str) -> None:
        """Merge video and subtitle without audio"""
        try:
            # Read subtitle text from file
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                subtitle_content = f.read()
                # Extract subtitle text (assuming SRT format with text on the third line)
                subtitle_lines = subtitle_content.split('\n')
                subtitle_text = subtitle_lines[2] if len(subtitle_lines) > 2 else ""
                
            logger.info(f"Merging video with subtitle text only (no audio): {subtitle_text}")
            
            # Check if input is an image (png, jpg, etc.) that needs to be converted to video
            is_image = os.path.splitext(video_path)[1].lower() in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
            
            # Create a temporary file for the video if needed
            temp_video_path = f"{os.path.splitext(output_path)[0]}_temp{os.path.splitext(output_path)[1]}"
            
            if is_image:
                # Convert image to video with a default duration
                default_duration = 10.0  # Default duration in seconds
                logger.info(f"Converting image to video with default duration {default_duration} seconds")
                image_to_video_cmd = [
                    self.ffmpeg_path,
                    '-loop', '1',  # Loop the image
                    '-i', video_path,  # Input image
                    '-c:v', 'libx264',  # Use H.264 codec
                    '-t', str(default_duration),  # Set default duration
                    '-pix_fmt', 'yuv420p',  # Required for compatibility
                    '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',  # Scale and pad to 1080p
                    '-y',  # Overwrite output
                    temp_video_path
                ]
                
                logger.info(f"Running image to video conversion")
                
                image_process = subprocess.run(
                    image_to_video_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if image_process.returncode != 0:
                    logger.error(f"ffmpeg image to video error: {image_process.stderr}")
                    raise Exception(f"ffmpeg image to video error: {image_process.stderr}")
                
                # Now use the generated video for further processing
                video_path = temp_video_path
                
            # Create a temporary file for the video with hardcoded subtitles
            subtitle_video_path = f"{os.path.splitext(output_path)[0]}_subtitle_temp{os.path.splitext(output_path)[1]}"
            
            # Add subtitles to the video and set resolution to 1920x1080 (standard HD)
            # Using Alignment=2 for top center positioning
            subtitle_cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-vf', f"subtitles='{subtitle_path.replace('\\', '/')}':force_style='FontSize=24,FontName=Arial,Alignment=2,BorderStyle=1,Outline=2,Shadow=0,MarginV=50,PrimaryColour=&HFFFFFF,OutlineColour=&H000000',scale=1920:1080",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-y',
                subtitle_video_path
            ]
            
            logger.info(f"Running subtitle embedding command")
            
            # Run ffmpeg command to add subtitles
            subtitle_process = subprocess.run(
                subtitle_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if subtitle_process.returncode != 0:
                logger.error(f"ffmpeg subtitle error: {subtitle_process.stderr}")
                # If subtitles fail, try an alternative approach with drawtext filter
                logger.warning("Subtitle embedding failed, trying alternative method")
                
                # Try with drawtext filter instead and set resolution to 1920x1080 (standard HD)
                # Position subtitles at the top center of the frame
                alt_subtitle_cmd = [
                    self.ffmpeg_path,
                    '-i', video_path,
                    '-vf', f"drawtext=text='{subtitle_text.replace("'", "\'").replace('"', '\"')}':fontcolor=white:fontsize=24:fontname=Arial:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=50,scale=1920:1080",
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-y',
                    subtitle_video_path
                ]
                
                logger.info(f"Running alternative subtitle embedding command with drawtext")
                
                alt_subtitle_process = subprocess.run(
                    alt_subtitle_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if alt_subtitle_process.returncode != 0:
                    logger.error(f"Alternative subtitle method failed: {alt_subtitle_process.stderr}")
                    logger.warning("All subtitle methods failed, using video without subtitles")
                    subtitle_video_path = video_path
            
            # Copy the subtitle video as the final output (no audio to merge)
            if subtitle_video_path != output_path:
                shutil.copy2(subtitle_video_path, output_path)
            
            # Clean up temporary files if they were created
            for temp_file in [temp_video_path, subtitle_video_path]:
                if temp_file != video_path and temp_file != output_path and os.path.exists(temp_file):
                    os.remove(temp_file)
                
        except Exception as e:
            logger.error(f"Error merging video with subtitle only: {str(e)}")
            raise Exception(f"Failed to merge video with subtitle only: {str(e)}")
    
    async def _concatenate_videos(self, input_files: List[str], output_path: str) -> None:
        """Concatenate multiple video files into one"""
        try:
            # Create a temporary file listing all input files
            concat_list_path = os.path.join(os.path.dirname(output_path), "concat_list.txt")
            
            with open(concat_list_path, 'w') as f:
                for file_path in input_files:
                    # Use absolute path with file protocol and proper escaping
                    abs_path = os.path.abspath(file_path)
                    f.write(f"file '{abs_path.replace('\\', '/')}' \n")
            
            # Build ffmpeg command for concatenation
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list_path,
                '-c', 'copy',
                '-y',  # Overwrite output file if it exists
                output_path
            ]
            
            # Run ffmpeg command using subprocess
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if process.returncode != 0:
                logger.error(f"ffmpeg concatenation error: {process.stderr}")
                raise Exception(f"ffmpeg concatenation error: {process.stderr}")
            
            # Clean up the temporary concat list file
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)
                
        except Exception as e:
            logger.error(f"Error concatenating videos: {str(e)}")
            raise Exception(f"Failed to concatenate videos: {str(e)}")

    async def check_ffmpeg_availability(self) -> bool:
        """Check if ffmpeg is available and working"""
        try:
            # Run a simple ffmpeg command to check if it's working
            cmd = [
                self.ffmpeg_path,
                '-version'
            ]
            
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if process.returncode == 0:
                logger.info(f"ffmpeg is available: {process.stdout.splitlines()[0] if process.stdout else ''}")
                return True
            else:
                logger.error(f"ffmpeg check failed: {process.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error checking ffmpeg: {str(e)}")
            return False


# Create a singleton instance
media_merge_service = MediaMergeService()
