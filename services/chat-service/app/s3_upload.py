import boto3
import uuid
import os
from fastapi import HTTPException, UploadFile
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_REGION", "eu-north-1")
S3_BUCKET_NAME        = os.getenv("S3_BUCKET_NAME")

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp"
}
ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo"
}
ALLOWED_TYPES   = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES
MAX_FILE_SIZE   = 30 * 1024 * 1024    # 30MB
MAX_IMAGE_SIZE  = 10 * 1024 * 1024    # 10MB for images
MAX_VIDEO_SIZE  = 30 * 1024 * 1024    # 30MB for videos


def get_s3_client():
    return boto3.client(
        "s3",
        region_name           = AWS_REGION,
        aws_access_key_id     = AWS_ACCESS_KEY_ID,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY
    )


async def validate_and_upload(file: UploadFile) -> dict:

    # validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code = 400,
            detail      = "File type not allowed. Only JPEG, PNG, GIF, WEBP images and MP4, MOV, WEBM videos are accepted."
        )

    # read content
    content = await file.read()

    # validate not empty
    if len(content) == 0:
        raise HTTPException(
            status_code = 400,
            detail      = "File is empty"
        )

    # validate size per type
    if file.content_type in ALLOWED_IMAGE_TYPES:
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code = 400,
                detail      = "Image too large. Maximum size is 10MB"
            )
        file_type   = "image"
        folder      = "images"

    else:
        if len(content) > MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code = 400,
                detail      = "Video too large. Maximum size is 30MB"
            )
        file_type   = "video"
        folder      = "videos"

    # generate unique key
    extension   = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    unique_key  = f"{folder}/{uuid.uuid4()}.{extension}"

    # upload to S3
    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket      = S3_BUCKET_NAME,
            Key         = unique_key,
            Body        = content,
            ContentType = file.content_type,
        )

        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_key}"

        return {
            "url":       file_url,
            "file_type": file_type,
            "file_name": file.filename,
            "file_size": len(content)
        }

    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"Upload to storage failed: {str(e)}"
        )