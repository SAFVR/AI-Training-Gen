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
                # Create output path for intermediate file
                intermediate_file = f"{temp_dir}/temp_clip_{i+1}.mp4"
                intermediate_files.append(intermediate_file)
                
                # Create subtitle file
                subtitle_file = f"{temp_dir}/subtitle_{i+1}.srt"
                await self._create_subtitle_file(subtitle_file, subtitle)
                
                # Merge video and audio using ffmpeg
                await self._merge_video_audio_subtitle(video_path, audio_path, subtitle_file, intermediate_file)
                
                logger.info(f"Created intermediate clip {i+1} with audio and subtitles")
            
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
    
    async def _create_subtitle_file(self, subtitle_file: str, subtitle_text: str) -> None:
        """Create a simple SRT subtitle file"""
        try:
            logger.info(f"Creating subtitle file with text: {subtitle_text}")
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                f.write("1\n")
                f.write("00:00:00,000 --> 00:00:10,000\n")
                f.write(f"{subtitle_text}\n")
            logger.info(f"Subtitle file created successfully: {subtitle_file}")
        except Exception as e:
            logger.error(f"Error creating subtitle file: {str(e)}")
            raise Exception(f"Failed to create subtitle file: {str(e)}")
    
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
            
            # Create a temporary file for the video with hardcoded subtitles
            temp_video_path = f"{os.path.splitext(output_path)[0]}_temp{os.path.splitext(output_path)[1]}"
            
            # First, add subtitles to the video and set resolution to 1920x1080 (standard HD)
            subtitle_cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-vf', f"subtitles='{subtitle_path.replace('\\', '/')}':force_style='FontSize=24,Alignment=10,BorderStyle=3,Outline=1,Shadow=0,MarginV=35',scale=1920:1080",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-y',
                temp_video_path
            ]
            
            logger.info(f"Running subtitle embedding command: {' '.join(subtitle_cmd)}")
            
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
                alt_subtitle_cmd = [
                    self.ffmpeg_path,
                    '-i', video_path,
                    '-vf', f"drawtext=text='{subtitle_text.replace("'", "\'").replace('"', '\"')}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=h-th-20,scale=1920:1080",
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-y',
                    temp_video_path
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
                    temp_video_path = video_path
            
            # Now merge the video with audio
            audio_cmd = [
                self.ffmpeg_path,
                '-i', temp_video_path,
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
            
            # Clean up temporary file if it was created
            if temp_video_path != video_path and os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            
            if audio_process.returncode != 0:
                logger.error(f"ffmpeg audio error: {audio_process.stderr}")
                raise Exception(f"ffmpeg audio error: {audio_process.stderr}")
                
        except Exception as e:
            logger.error(f"Error merging video and audio: {str(e)}")
            raise Exception(f"Failed to merge video and audio: {str(e)}")
    
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