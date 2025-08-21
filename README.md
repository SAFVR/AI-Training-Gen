# AI Training Video Generator

A FastAPI application that generates training videos based on job descriptions using AI services.

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

Edit the `.env` file and add your API keys and configuration.

## Usage

1. Start the server

```bash
python main.py
```

2. The API will be available at `http://localhost:8000`

3. Use the `/api/generate_video` endpoint with a POST request containing the required job information:

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