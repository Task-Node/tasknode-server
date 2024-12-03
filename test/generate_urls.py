import boto3
from datetime import datetime
import json


def generate_presigned_urls():
    s3_client = boto3.client("s3")

    # Configure buckets and job ID
    job_id = f"test-job-{int(datetime.now().timestamp())}"
    bucket = "tasknode-file-drop-dev"
    processed_bucket = "tasknode-processed-files-dev"

    # Generate download URL (60 second expiry)
    download_url = s3_client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": "134663f0-0b33-403c-86be-2c715829155d.zip"}, ExpiresIn=60
    )

    # Generate upload URLs (24 hour expiry)
    upload_urls = {
        "zip": s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": processed_bucket, "Key": f"{job_id}/files.zip", "ContentType": "application/zip"},
            ExpiresIn=86400,
        ),
        "manifest": s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": processed_bucket, "Key": f"{job_id}/manifest.txt", "ContentType": "text/plain"},
            ExpiresIn=86400,
        ),
        "output_log": s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": processed_bucket, "Key": f"{job_id}/output.log", "ContentType": "text/plain"},
            ExpiresIn=86400,
        ),
        "error_log": s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": processed_bucket, "Key": f"{job_id}/error.log", "ContentType": "text/plain"},
            ExpiresIn=86400,
        ),
    }

    return {"job_id": job_id, "download_url": download_url, **upload_urls}


if __name__ == "__main__":
    urls = generate_presigned_urls()
    print(json.dumps(urls, indent=2))
