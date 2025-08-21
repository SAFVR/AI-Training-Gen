from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # LiteLLM settings
    LITELLM_BASE_URL: str
    LITELLM_API_KEY: str
    LITELLM_MODEL_ID: str
    
    # BytePulse API settings
    BYTEPULSE_API_KEY: str
    BYTEPULSE_API_URL: str = "https://api.bytepulse.ai/v1"
    BYTEPULSE_MODEL: str
    
    # ElevenLabs API settings
    ELEVENLABS_API_KEY: str
    ELEVENLABS_API_URL: str = "https://api.elevenlabs.io/v1"
    ELEVENLABS_VOICE_ID: str
    
    # Azure AI settings
    AZURE_AI_ENDPOINT: str
    AZURE_AI_API_KEY: str
    AZURE_AI_MODEL_ID: str
    
    # Creatomate API settings
    CREATOMATE_API_KEY: str
    CREATOMATE_TEMPLATE_ID: str
    
    # AWS S3 settings
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()