import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.core.config import settings

# Load environment variables
load_dotenv()

# Configure logger
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="1 week",
    level="INFO",
    backtrace=True,
    diagnose=True,
)

# Create FastAPI app
app = FastAPI(
    title="AI Training Video Generator",
    description="API for generating training videos based on job descriptions",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Create necessary directories
os.makedirs("video", exist_ok=True)
os.makedirs("logs", exist_ok=True)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )