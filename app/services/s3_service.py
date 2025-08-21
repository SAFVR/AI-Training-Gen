import os
import boto3
from botocore.exceptions import ClientError
from loguru import logger
from typing import Optional

from app.core.config import settings

class S3Service:
    def __init__(self):
        self.access_key = settings.AWS_ACCESS_KEY_ID
        self.secret_key = settings.AWS_SECRET_ACCESS_KEY
        self.region = settings.AWS_REGION
        self.bucket_name = settings.AWS_S3_BUCKET
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        ) if self.access_key and self.secret_key else None
    
    async def upload_file(self, file_path: str, object_name: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to an S3 bucket and return the public URL
        
        :param file_path: Path to the file to upload
        :param object_name: S3 object name. If not specified, file_path's basename is used
        :return: Public URL of the uploaded file if successful, None otherwise
        """
        if not self.s3_client or not self.bucket_name:
            logger.warning("S3 client not initialized or bucket name not set")
            return None
            
        # If S3 object_name was not specified, use file_path's basename
        if object_name is None:
            object_name = os.path.basename(file_path)
        
        try:
            logger.info(f"Uploading file {file_path} to S3 bucket {self.bucket_name}")
            
            # Get file size for logging
            file_size = os.path.getsize(file_path)
            logger.info(f"File size: {file_size / (1024 * 1024):.2f} MB")
            
            # Upload the file
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            
            # Generate the URL for the uploaded file
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_name}"
            logger.info(f"File uploaded successfully to {url}")
            return url
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading file to S3: {str(e)}")
            return None

# Create a singleton instance
s3_service = S3Service()