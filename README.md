# AI Training Video Generator

A FastAPI application that generates training videos based on job descriptions using AI services.

## Important Repository Information

This repository has been restructured to exclude large binary files. The `new_main` branch is a clean branch that excludes FFmpeg binaries and sensitive credentials. When working with this repository:

1. Always use the `new_main` branch for development
2. Do not attempt to push the old `main` branch as it contains files exceeding GitHub's size limits
3. Follow the FFmpeg setup instructions below to manually add the required binary files

## Features

- Analyzes job descriptions to identify safety risks
- Generates comprehensive course outlines
- Creates video segmentation for training content
- Produces video clips with narration and subtitles
- Supports both video and image-based content generation
- Assembles final training videos with professional quality

## Requirements

- Python 3.8+
- FastAPI
- Pydantic
- httpx
- python-dotenv
- loguru
- movie-py

## Installation

1. Clone the repository

```bash
git clone https://github.com/your-username/ai-training-gen.git
cd ai-training-gen
```

2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Set up environment variables

```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys and configuration. Make sure to set up all required services:

- LiteLLM for AI text generation
- BytePulse for video generation
- ElevenLabs for audio narration
- Azure AI for image generation
- Creatomate for video processing with captions
- AWS S3 for video storage

5. FFmpeg Setup

This project requires FFmpeg executables which are not included in the Git repository due to their large file size. You'll need to download and set them up manually:

```bash
# For Windows:
# 1. Download FFmpeg from https://ffmpeg.org/download.html
# 2. Extract the files to the bin/ffmpeg-master-latest-win64-gpl/bin/ directory
# 3. Also copy ffmpeg.exe to the bin/ directory

# For macOS:
# brew install ffmpeg
# Then create symbolic links to the bin/ directory

# For Linux:
# apt-get install ffmpeg
# Then create symbolic links to the bin/ directory
```

The required files are:
- bin/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe
- bin/ffmpeg-master-latest-win64-gpl/bin/ffplay.exe
- bin/ffmpeg-master-latest-win64-gpl/bin/ffprobe.exe
- bin/ffmpeg.exe (copy of the above ffmpeg.exe)

Alternatively, you can download these files from our shared storage location (contact team lead for access).

## Creatomate Setup

1. Sign up for a Creatomate account at [https://creatomate.com](https://creatomate.com)
2. Create a new template for video captions or use an existing one
3. Get your API key from the Creatomate dashboard
4. Add your API key and template ID to the `.env` file:
   ```
   CREATOMATE_API_KEY=your_creatomate_api_key
   CREATOMATE_TEMPLATE_ID=your_creatomate_template_id
   ```

## AWS S3 Setup

1. Create an AWS account if you don't have one
2. Create an S3 bucket for storing videos
3. Create an IAM user with programmatic access and S3 permissions
4. Add your AWS credentials to the `.env` file:
   ```
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   AWS_REGION=your_aws_region
   AWS_S3_BUCKET=your_s3_bucket_name
   ```
5. Make sure your S3 bucket has the appropriate CORS configuration for video access

## Usage

1. Start the server

```bash
python main.py
```

2. The API will be available at `http://localhost:8000`

3. Available endpoints:

### Generate Video

Use the `/api/generate_video` endpoint with a POST request containing the required job information:

```json
{
  "job_title": "Construction Site Manager",
  "job_description": "Oversees construction projects, ensures safety protocols are followed, and manages workers on site.",
  "location": "Construction site",
  "equipment_used": "Heavy machinery, power tools, safety equipment",
  "industry_sector": "Construction",
  "video_type": "video"
}
```

The response will include:
- `video_url`: Local URL of the generated video
- `s3_video_url`: S3 URL of the uploaded video
- `creatomate_video_url`: URL of the video processed by Creatomate with captions

### Caption Generator

Use the `/api/caption_generator` endpoint to process an existing S3 video with Creatomate for caption generation:

```
POST /api/caption_generator
Content-Type: application/json

{
  "title": "Video Title",
  "description": "Video Description (optional)",
  "video_url": "https://your-s3-bucket.s3.amazonaws.com/your-video.mp4"
}
```

The response will include:
- `original_video_url`: S3 URL of the original video
- `creatomate_video_url`: URL of the video processed by Creatomate with captions
- `title`: Title of the video
- `description`: Description of the video (if provided)
- `created_at`: Timestamp of when the video was processed

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
.
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── azure_ai_service.py
│   │   ├── bytepulse_service.py
│   │   ├── creatomate_service.py
│   │   ├── elevenlabs_service.py
│   │   ├── litellm_service.py
│   │   └── video_generation_service.py
│   └── __init__.py
├── logs/
├── temp/
├── video/
├── .env
├── .env.example
├── main.py
├── README.md
└── requirements.txt
```

## License

MIT