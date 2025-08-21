from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

class VideoType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"

class VideoGenerationRequest(BaseModel):
    job_title: str = Field(..., description="Title of the job")
    job_description: str = Field(..., description="Description of the job")
    location: str = Field(..., description="Location where the job is performed")
    equipment_used: str = Field(..., description="Equipment used in the job")
    industry_sector: str = Field(..., description="Industry sector of the job")
    video_type: VideoType = Field(..., description="Type of video to generate (image or video)")

class VideoClipPrompt(BaseModel):
    video_prompt: str = Field(..., description="Prompt for video generation")
    audio_prompt: str = Field(..., description="Prompt for audio narration")
    subtitle_text: str = Field(..., description="Text for subtitles")

class VideoSegmentation(BaseModel):
    clips: List[VideoClipPrompt] = Field(..., description="List of video clip prompts")

class CourseOutline(BaseModel):
    title: str = Field(..., description="Title of the course")
    description: str = Field(..., description="Description of the course")
    sections: List[str] = Field(..., description="List of course sections")

class RiskAnalysis(BaseModel):
    risks: List[str] = Field(..., description="List of identified risks")
    severity_levels: List[str] = Field(..., description="Severity levels of identified risks")
    mitigation_strategies: List[str] = Field(..., description="Strategies to mitigate identified risks")

class VideoGenerationResponse(BaseModel):
    video_url: str = Field(..., description="URL of the generated video")
    creatomate_video_url: Optional[str] = Field(None, description="URL of the video processed by Creatomate")
    job_title: str = Field(..., description="Title of the job")
    course_title: str = Field(..., description="Title of the generated course")
    duration: float = Field(..., description="Duration of the video in seconds")
    clip_count: int = Field(..., description="Number of clips in the video")
    video_type: VideoType = Field(..., description="Type of video generated (image or video)")
    created_at: str = Field(..., description="Timestamp of video creation")