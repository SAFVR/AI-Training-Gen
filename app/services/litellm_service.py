import httpx
import json
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.config import settings

class LiteLLMService:
    def __init__(self):
        self.base_url = settings.LITELLM_BASE_URL
        self.api_key = settings.LITELLM_API_KEY
        self.model_id = settings.LITELLM_MODEL_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a completion using LiteLLM API"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
                
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_id,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
                
            logger.error(f"LiteLLM API error: Status {e.response.status_code} - {error_detail}")
            raise Exception(f"LiteLLM API error: {e.response.status_code} - {error_detail}") from e
            
        except httpx.RequestError as e:
            logger.error(f"LiteLLM connection error: {str(e)}")
            raise Exception(f"Failed to connect to LiteLLM API: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            raise Exception(f"LiteLLM completion generation failed: {str(e)}") from e
    
    async def generate_risk_analysis(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate risk analysis based on job data"""
        system_prompt = """You are a workplace safety expert. Analyze the job description and identify potential risks, 
        their severity levels, and mitigation strategies. Format your response as JSON with the following structure: 
        {"risks": ["risk1", "risk2"], "severity_levels": ["high", "medium"], "mitigation_strategies": ["strategy1", "strategy2"]}"""
        
        prompt = f"""Perform a detailed risk analysis for the following job:
        Job Title: {job_data['job_title']}
        Job Description: {job_data['job_description']}
        Location: {job_data['location']}
        Equipment Used: {job_data['equipment_used']}
        Industry Sector: {job_data['industry_sector']}
        
        Identify at least 5 potential risks, their severity levels, and mitigation strategies."""
        
        try:
            result = await self.generate_completion(prompt, system_prompt)
            return json.loads(result)
        except json.JSONDecodeError:
            logger.error("Failed to parse risk analysis response as JSON")
            # Fallback to a simple structure if JSON parsing fails
            return {
                "risks": ["Error parsing risk analysis"],
                "severity_levels": ["unknown"],
                "mitigation_strategies": ["Retry analysis"]
            }
    
    async def generate_course_outline(self, job_data: Dict[str, Any], risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate course outline based on job data and risk analysis"""
        system_prompt = """You are a training course designer. Create a comprehensive course outline based on the job description 
        and risk analysis. Format your response as JSON with the following structure: 
        {"title": "Course Title", "description": "Course description", "sections": ["section1", "section2"]}"""
        
        risks_str = "\n".join([f"- {risk}" for risk in risk_analysis["risks"]])
        mitigation_str = "\n".join([f"- {strategy}" for strategy in risk_analysis["mitigation_strategies"]])
        
        prompt = f"""Create a comprehensive safety training course outline for the following job:
        Job Title: {job_data['job_title']}
        Job Description: {job_data['job_description']}
        Location: {job_data['location']}
        Equipment Used: {job_data['equipment_used']}
        Industry Sector: {job_data['industry_sector']}
        
        Key Risks to Address:
        {risks_str}
        
        Mitigation Strategies to Include:
        {mitigation_str}
        
        Create a course with a compelling title, description, and at least 6 main sections."""
        
        try:
            result = await self.generate_completion(prompt, system_prompt)
            return json.loads(result)
        except json.JSONDecodeError:
            logger.error("Failed to parse course outline response as JSON")
            # Fallback to a simple structure if JSON parsing fails
            return {
                "title": f"Safety Training for {job_data['job_title']}",
                "description": "Comprehensive safety training course",
                "sections": ["Introduction", "Safety Basics", "Equipment Safety", "Emergency Procedures", "Best Practices", "Assessment"]
            }
    
    async def generate_video_segmentation(self, job_data: Dict[str, Any], course_outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate video segmentation based on course outline"""
        system_prompt = """You are a video production expert specializing in safety training videos. 
        Create a detailed segmentation for a training video based on the provided course outline. 
        Format your response as JSON with an array of 18 segments, each containing a brief description of what should be covered in that segment."""
        
        sections_str = "\n".join([f"- {section}" for section in course_outline["sections"]])
        
        # Handle different schema versions - check for required fields
        location = job_data.get('location', 'Not specified')
        equipment_used = job_data.get('equipment_used', 'Not specified')
        industry = job_data.get('industry', job_data.get('industry_sector', 'Not specified'))
        target_audience = job_data.get('target_audience', 'Workers')
        key_points = job_data.get('key_points', [])
        
        # Format key points if available
        key_points_str = "\n".join([f"- {point}" for point in key_points]) if key_points else "Not specified"
        
        prompt = f"""Create a detailed segmentation for a training video based on the following course outline:
        Course Title: {course_outline['title']}
        Course Description: {course_outline['description']}
        
        Course Sections:
        {sections_str}
        
        Job Details:
        Job Title: {job_data['job_title']}
        Job Description: {job_data['job_description']}
        Industry: {industry}
        Target Audience: {target_audience}
        
        Additional Information (if available):
        Location: {location}
        Equipment Used: {equipment_used}
        Key Points: {key_points_str}
        
        Create exactly 18 video segments that cover the entire course content. Each segment should be focused on a specific topic or skill."""
        
        try:
            result = await self.generate_completion(prompt, system_prompt)
            # Handle potential JSON format issues
            try:
                segments = json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse video segmentation response as JSON: {e}")
                # Try to extract JSON from the response if it contains other text
                import re
                json_match = re.search(r'\[\s*{.*}\s*\]', result, re.DOTALL)
                if json_match:
                    try:
                        segments = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        raise  # If this also fails, go to the outer exception handler
                else:
                    raise  # If no JSON-like pattern found, go to the outer exception handler
            
            # Validate segments structure
            if not isinstance(segments, list):
                logger.warning(f"Expected segments to be a list, got {type(segments)}")
                if isinstance(segments, dict) and "segments" in segments:
                    # Handle case where API returns {"segments": [...]} instead of directly [...]  
                    segments = segments["segments"]
                else:
                    # Create a default list if segments is not a list
                    segments = []
            
            # Ensure we have exactly 18 segments
            if len(segments) > 18:
                segments = segments[:18]
            elif len(segments) < 18:
                # Pad with generic segments if needed
                for i in range(len(segments), 18):
                    segments.append({"description": f"Additional safety information part {i+1}"})
            
            # Ensure each segment is a dictionary with a description field
            for i in range(len(segments)):
                segment = segments[i]
                if not isinstance(segment, dict):
                    segments[i] = {"description": str(segment)}
                elif "description" not in segment:
                    segments[i] = {**segment, "description": f"Segment {i+1}"}
            
            return segments
        except json.JSONDecodeError:
            logger.error("Failed to parse video segmentation response as JSON")
            # Fallback to a simple structure if JSON parsing fails
            segments = []
            for i in range(18):
                description = f"Segment {i+1}"
                if i < len(course_outline['sections']):
                    description += f": {course_outline['sections'][i]}"
                else:
                    description += ": Additional safety information"
                segments.append({"description": description})
            return segments
    
    async def generate_video_clip_prompts(self, job_data: Dict[str, Any], segmentation: List[Dict[str, Any]], video_type: str) -> List[Dict[str, Any]]:
        """Generate video clip prompts based on segmentation"""
        system_prompt = """You are a creative director for training videos. For each segment, create prompts for video generation, 
        audio narration, and subtitle text. Format your response as JSON with an array of 18 objects, each containing 
        'video_prompt', 'audio_prompt', and 'subtitle_text' fields."""
        
        # Ensure each segment has a description field
        segment_descriptions = []
        for i, segment in enumerate(segmentation):
            if isinstance(segment, dict) and "description" in segment:
                segment_descriptions.append(segment["description"])
            elif isinstance(segment, dict):
                segment_descriptions.append(f"Segment {i+1}")
            else:
                segment_descriptions.append(f"Segment {i+1}: {str(segment)}")
        
        segments_str = "\n".join([f"- Segment {i+1}: {desc}" for i, desc in enumerate(segment_descriptions)])
        
        # Handle different schema versions - check for required fields
        location = job_data.get('location', 'Not specified')
        equipment_used = job_data.get('equipment_used', 'Not specified')
        industry = job_data.get('industry', job_data.get('industry_sector', 'Not specified'))
        target_audience = job_data.get('target_audience', 'Workers')
        key_points = job_data.get('key_points', [])
        
        # Format key points if available
        key_points_str = "\n".join([f"- {point}" for point in key_points]) if key_points else "Not specified"
        
        prompt = f"""Create detailed prompts for a training video with the following segments:
        {segments_str}
        
        Job Details:
        Job Title: {job_data.get('job_title', 'Safety Training')}
        Job Description: {job_data.get('job_description', 'Safety training for workers')}
        Industry: {industry}
        Target Audience: {target_audience}
        
        Additional Information (if available):
        Location: {location}
        Equipment Used: {equipment_used}
        Key Points: {key_points_str}
        Video Type: {video_type}
        
        For each of the 18 segments, create:
        1. A detailed {'image generation prompt' if video_type == 'image' else 'video generation prompt'} that describes the visual content
        2. An audio narration prompt that provides the script for the narrator
        3. A short, title-style subtitle text (max 10 words) that aligns with the narration
        
        Make the prompts specific, detailed, and aligned with workplace safety training."""
        
        try:
            result = await self.generate_completion(prompt, system_prompt)
            
            # Handle potential JSON format issues
            try:
                clip_prompts = json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse video clip prompts response as JSON: {e}")
                # Try to extract JSON from the response if it contains other text
                import re
                json_match = re.search(r'\[\s*{.*}\s*\]', result, re.DOTALL)
                if json_match:
                    try:
                        clip_prompts = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        raise  # If this also fails, go to the outer exception handler
                else:
                    raise  # If no JSON-like pattern found, go to the outer exception handler
            
            # Validate clip_prompts structure
            if not isinstance(clip_prompts, list):
                logger.warning(f"Expected clip_prompts to be a list, got {type(clip_prompts)}")
                if isinstance(clip_prompts, dict) and any(key in clip_prompts for key in ["prompts", "clips", "segments"]):
                    # Handle case where API returns {"prompts": [...]} instead of directly [...]
                    for key in ["prompts", "clips", "segments"]:
                        if key in clip_prompts:
                            clip_prompts = clip_prompts[key]
                            break
                else:
                    # Create a default list if clip_prompts is not a list
                    clip_prompts = []
            
            # Ensure we have exactly 18 clip prompts with all required fields
            if len(clip_prompts) > 18:
                clip_prompts = clip_prompts[:18]
            elif len(clip_prompts) < 18:
                # Pad with generic prompts if needed
                for i in range(len(clip_prompts), 18):
                    clip_prompts.append({
                        "video_prompt": f"Safety training visual for segment {i+1}",
                        "audio_prompt": f"Narration for safety segment {i+1}",
                        "subtitle_text": f"Safety Tip #{i+1}"
                    })
            
            # Ensure all required fields are present
            for i in range(len(clip_prompts)):
                prompt_obj = clip_prompts[i]
                if not isinstance(prompt_obj, dict):
                    clip_prompts[i] = {
                        "video_prompt": f"Safety training visual for segment {i+1}",
                        "audio_prompt": f"Narration for safety segment {i+1}",
                        "subtitle_text": f"Safety Tip #{i+1}"
                    }
                    continue
                    
                if "video_prompt" not in prompt_obj:
                    prompt_obj["video_prompt"] = f"Safety training visual for segment {i+1}"
                if "audio_prompt" not in prompt_obj:
                    prompt_obj["audio_prompt"] = f"Narration for safety segment {i+1}"
                if "subtitle_text" not in prompt_obj:
                    prompt_obj["subtitle_text"] = f"Safety Tip #{i+1}"
            
            return clip_prompts
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            logger.error(f"Error processing video clip prompts: {str(e)}")
            # Log the raw response for debugging
            logger.debug(f"Raw response that caused the error: {result[:500]}..." if len(result) > 500 else result)
            
            # Create segment descriptions for fallback prompts
            segment_texts = []
            for i in range(18):
                if i < len(segmentation) and isinstance(segmentation[i], dict) and "description" in segmentation[i]:
                    segment_texts.append(segmentation[i]["description"])
                else:
                    segment_texts.append(f"Safety segment {i+1}")
            
            # Fallback to a simple structure if JSON parsing fails
            return [{
                "video_prompt": f"Safety training visual showing {segment_texts[i]}",
                "audio_prompt": f"Narration explaining {segment_texts[i]}",
                "subtitle_text": f"Safety: {segment_texts[i][:30]}" if len(segment_texts[i]) > 30 else segment_texts[i]
            } for i in range(18)]

# Create a singleton instance
litellm_service = LiteLLMService()