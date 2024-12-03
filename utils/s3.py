import boto3
from config import settings
from utils.logger import logger


def download_file(bucket_name: str, file_name: str, local_file_path: str) -> bool:
    """
    Downloads a file from an S3 bucket
    """
    # Create an S3 client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    s3 = boto_session.client("s3")

    # Download the file
    try:
        s3.download_file(bucket_name, file_name, local_file_path)
    except Exception as e:
        logger.error(f"Error downloading file from S3: {str(e)}")
        return False

    return True


def upload_file(file_binary: bytes, bucket_name: str, file_name: str) -> bool:
    """
    Uploads a file to an S3 bucket
    """
    # Create an S3 client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    s3 = boto_session.client("s3")

    # Upload the file
    try:
        s3.put_object(Bucket=bucket_name, Key=f"{file_name}", Body=file_binary)
    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        return False

    return True


def delete_file(bucket_name: str, file_name: str) -> bool:
    """
    Deletes a file from an S3 bucket
    """
    # Create an S3 client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    s3 = boto_session.client("s3")

    # Delete the file
    try:
        s3.delete_object(Bucket=bucket_name, Key=file_name)
    except Exception as e:
        logger.error(f"Error deleting file from S3: {str(e)}")
        return False

    return True


def copy_file(source_bucket: str, source_key: str, destination_bucket: str, destination_key: str) -> bool:
    """
    Copies a file from one S3 bucket to another
    """
    # Create an S3 client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    s3 = boto_session.client("s3")

    # Copy the file
    try:
        s3.copy_object(
            Bucket=destination_bucket,
            CopySource={"Bucket": source_bucket, "Key": source_key},
            Key=destination_key,
        )
    except Exception as e:
        logger.error(f"Error copying file from one S3 bucket to another: {str(e)}")
        return False

    return True


def get_signed_url(bucket_name: str, file_key: str, expiration: int = 60) -> str:
    """
    Generates a presigned URL for a file in an S3 bucket
    """
    # Create an S3 client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    s3 = boto_session.client("s3")

    # Generate the presigned URL
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": file_key},
            ExpiresIn=expiration,
        )
    except Exception as e:
        logger.error(f"Error generating presigned URL for file in S3: {str(e)}")
        return ""

    return url


def get_signed_upload_url(
    bucket_name: str, file_key: str, content_type: str, expiration: int = 60, cognito_id: str = None
) -> str:
    """
    Generates a presigned URL for a file in an S3 bucket
    """
    # Create an S3 client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    s3 = boto_session.client("s3")

    params = {
        "Bucket": bucket_name,
        "Key": file_key,
        "ContentType": content_type,
        "Metadata": {"cognito_id": cognito_id},
    }

    # Generate the presigned URL
    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=expiration,
        )
    except Exception as e:
        logger.error(f"Error generating presigned URL for file in S3: {str(e)}")
        return ""

    return url


def get_file_metadata(bucket_name: str, file_key: str) -> dict:
    """
    Gets the metadata for a file in an S3 bucket
    """
    # Create an S3 client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    s3 = boto_session.client("s3")

    # Get the file metadata
    try:
        metadata = s3.head_object(Bucket=bucket_name, Key=file_key)
    except Exception as e:
        logger.error(f"Error getting file metadata from S3: {str(e)}")
        return {}

    return metadata


def get_all_files_in_bucket(bucket_name: str) -> list:
    """
    Gets all the files in an S3 bucket
    """
    # Create an S3 client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    s3 = boto_session.client("s3")

    try:
        files = s3.list_objects_v2(Bucket=bucket_name)["Contents"]
    except Exception as e:
        logger.error(f"Error getting all files in S3 bucket: {str(e)}")
        return []

    return files
