#!/bin/bash

# Set AWS credentials if not already set in environment
# export AWS_ACCESS_KEY_ID="your-access-key"
# export AWS_SECRET_ACCESS_KEY="your-secret-key"
# export AWS_DEFAULT_REGION="your-region"

# Generate presigned URLs using Python script
URLS_JSON=$(python3 generate_urls.py)

# Extract URLs from JSON
DOWNLOAD_URL=$(echo $URLS_JSON | jq -r '.download_url')
ZIP_UPLOAD_URL=$(echo $URLS_JSON | jq -r '.zip')
MANIFEST_UPLOAD_URL=$(echo $URLS_JSON | jq -r '.manifest')
OUTPUT_LOG_UPLOAD_URL=$(echo $URLS_JSON | jq -r '.output_log')
ERROR_LOG_UPLOAD_URL=$(echo $URLS_JSON | jq -r '.error_log')

# echo the URLs
echo "DOWNLOAD_URL: $DOWNLOAD_URL"
echo "ZIP_UPLOAD_URL: $ZIP_UPLOAD_URL"
echo "MANIFEST_UPLOAD_URL: $MANIFEST_UPLOAD_URL"
echo "OUTPUT_LOG_UPLOAD_URL: $OUTPUT_LOG_UPLOAD_URL"
echo "ERROR_LOG_UPLOAD_URL: $ERROR_LOG_UPLOAD_URL"

# Run Docker container with environment variables
# docker run \
#   -e DOWNLOAD_URL="$DOWNLOAD_URL" \
#   -e ZIP_UPLOAD_URL="$ZIP_UPLOAD_URL" \
#   -e MANIFEST_UPLOAD_URL="$MANIFEST_UPLOAD_URL" \
#   -e OUTPUT_LOG_UPLOAD_URL="$OUTPUT_LOG_UPLOAD_URL" \
#   -e ERROR_LOG_UPLOAD_URL="$ERROR_LOG_UPLOAD_URL" \
#   your-image-name:tag 