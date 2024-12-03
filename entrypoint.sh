#!/bin/sh

echo 'Job started'

# Install dependencies
apt-get update && \
apt-get install -y unzip curl zip jq && \
mkdir -p /app && cd /app

# Create a timestamp file that will be used to check if there are new files to zip
touch timestamp

# Download the input zip file and unzip it
echo "Downloading from: $DOWNLOAD_URL" && \
curl -v "$DOWNLOAD_URL" -o ./input.zip && \
echo 'Download complete. File details:' && \
ls -l input.zip && \
file input.zip && \
unzip -t input.zip || true && \
unzip input.zip && \
cd tasknode_deploy

# Check if run_info.json exists
if [ ! -f run_info.json ]; then
    echo 'Error: run_info.json not found' >&2
    exit 1
fi

# Install requirements
pip install -r requirements-tasknode.txt && \
echo 'Finished installing requirements'

cat run_info.json

echo '' && echo 'Running script'
SCRIPT_NAME=$(cat run_info.json | jq -r '.script')
echo "Script to run: $SCRIPT_NAME"
ls -l

# Run the script in background with unbuffered output
python -u "$SCRIPT_NAME" > tasknode_output.log 2> tasknode_error.log &
SCRIPT_PID=$!

# Upload logs every 30 seconds while script is running
while kill -0 $SCRIPT_PID 2>/dev/null; do
    echo "Uploading interim log files..."
    curl -H 'Content-Type: text/plain' -T tasknode_output.log "$OUTPUT_LOG_UPLOAD_URL" || echo 'Interim output log upload failed'
    curl -H 'Content-Type: text/plain' -T tasknode_error.log "$ERROR_LOG_UPLOAD_URL" || echo 'Interim error log upload failed'
    sleep 30
done

# Wait for script to finish
wait $SCRIPT_PID
SCRIPT_EXIT_CODE=$?

# Upload final logs
echo "Uploading final log files..."
curl -v -H 'Content-Type: text/plain' -T tasknode_output.log "$OUTPUT_LOG_UPLOAD_URL" || echo 'Final output log upload failed'
curl -v -H 'Content-Type: text/plain' -T tasknode_error.log "$ERROR_LOG_UPLOAD_URL" || echo 'Final error log upload failed'

# Exit with the script's exit code
if [ $SCRIPT_EXIT_CODE -ne 0 ]; then
    echo "Script failed with exit code $SCRIPT_EXIT_CODE"
    exit $SCRIPT_EXIT_CODE
fi

echo 'Script finished'

if [ ! -f tasknode_output.log ]; then
    echo 'Error: tasknode_output.log not found' >&2
    exit 1
fi

echo 'Output log found'

if [ ! -f tasknode_error.log ]; then
    echo 'Error log not found' >&2
    exit 1
fi

echo 'Error log found'


cd ..
FILES=$(find . -type f -newer /app/timestamp -print)
if [ -n "$FILES" ]; then
    echo 'Files to be zipped:'
    echo "$FILES"
    echo 'Found new files to zip'
    mkdir -p tasknode_outputs
    find tasknode_deploy -type f -newer /app/timestamp -not -name 'tasknode_*.log' -exec stat --format='%n,%s,%Y' {} \; > ./manifest.txt
    echo 'Manifest contents:'
    cat ./manifest.txt
    echo 'Uploading manifest file...'
    curl -v -H 'Content-Type: text/plain' -T ./manifest.txt "$MANIFEST_UPLOAD_URL" || echo 'Manifest upload failed with status: $?'
    find tasknode_deploy -type f -newer /app/timestamp -not -name 'tasknode_*.log' -exec cp {} tasknode_outputs/ \;
    zip -r tasknode_outputs.zip tasknode_outputs/
    echo 'Uploading generated files zip...'
    curl -v -H 'Content-Type: application/zip' -T tasknode_outputs.zip "$ZIP_UPLOAD_URL" || echo 'Zip upload failed with status: $?'
else
    echo 'No new generated files found'
    echo 'Creating empty manifest file...'
    touch ./manifest.txt
    curl -v -H 'Content-Type: text/plain' -T ./manifest.txt "$MANIFEST_UPLOAD_URL" || echo 'Empty manifest upload failed with status: $?'
fi

echo 'Job finished'