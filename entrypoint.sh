#!/bin/sh

echo 'Job started'

# Create working directory and change to it (removed apt-get installations)
mkdir -p /app && cd /app

# Create a timestamp file that will be used to check if there are new files to zip
touch timestamp

# Download the input zip file and unzip it
echo "Downloading from: $DOWNLOAD_URL" && \
curl -v "$DOWNLOAD_URL" -o ./input.zip || { echo 'Download failed' >&2; exit 1; } && \
echo 'Download complete. File details:' && \
ls -l input.zip && \
file input.zip || { echo 'File details failed' >&2; exit 1; } && \
unzip -t input.zip || { echo 'Unzip test failed' >&2; exit 1; } && \
mkdir -p tasknode_deploy && \
unzip input.zip -d tasknode_deploy || { echo 'Unzip failed' >&2; exit 1; } && \
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

# Convert notebook to python if it's a .ipynb file
if [ "$SCRIPT_NAME" = *.ipynb ]; then
    echo "Converting Jupyter notebook ($SCRIPT_NAME) to Python script..."
    jupyter nbconvert --to python "$SCRIPT_NAME" --output "${SCRIPT_NAME%.*}_converted"
    SCRIPT_NAME="${SCRIPT_NAME%.*}_converted.py"
    echo "New script to run: $SCRIPT_NAME"
fi

# Run the script in background with unbuffered output
python -u "$SCRIPT_NAME" > tasknode_output.log 2> tasknode_error.log &
SCRIPT_PID=$!

# Upload tail files every 5 seconds while script is running
while kill -0 $SCRIPT_PID 2>/dev/null; do
    echo "Uploading interim log tail files..."
    tail -n 100 tasknode_output.log > tasknode_output.tail
    tail -n 100 tasknode_error.log > tasknode_error.tail

    curl -H 'Content-Type: text/plain' -T tasknode_output.tail "$OUTPUT_TAIL_UPLOAD_URL" > /dev/null 2>&1 || echo 'Interim output tail upload failed'
    curl -H 'Content-Type: text/plain' -T tasknode_error.tail "$ERROR_TAIL_UPLOAD_URL" > /dev/null 2>&1 || echo 'Interim error tail upload failed'
    
    sleep 5
done

# Wait for script to finish
wait $SCRIPT_PID
SCRIPT_EXIT_CODE=$?

# Upload final logs and collect outputs
echo "Uploading final log files..."
curl -v -H 'Content-Type: text/plain' -T tasknode_output.log "$OUTPUT_LOG_UPLOAD_URL" > /dev/null 2>&1 || echo 'Final output log upload failed'
curl -v -H 'Content-Type: text/plain' -T tasknode_error.log "$ERROR_LOG_UPLOAD_URL" > /dev/null 2>&1 || echo 'Final error log upload failed'

# Create and upload tail files (last 20 lines)
echo "Creating and uploading tail files..."
tail -n 100 tasknode_output.log > tasknode_output.tail
tail -n 100 tasknode_error.log > tasknode_error.tail
curl -v -H 'Content-Type: text/plain' -T tasknode_output.tail "$OUTPUT_TAIL_UPLOAD_URL" > /dev/null 2>&1 || echo 'Output tail upload failed'
curl -v -H 'Content-Type: text/plain' -T tasknode_error.tail "$ERROR_TAIL_UPLOAD_URL" > /dev/null 2>&1 || echo 'Error tail upload failed'

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
    mkdir -p tasknode_generated_files
    cd tasknode_deploy
    find . -type f -newer /app/timestamp -not -name 'tasknode_*.log' -not -name 'tasknode_*.tail' -exec stat --format='%n,%s,%Y' {} \; > ../manifest.txt
    cd ..
    echo 'Manifest contents:'
    cat ./manifest.txt
    echo 'Uploading manifest file...'
    curl -v -H 'Content-Type: text/plain' -T ./manifest.txt "$MANIFEST_UPLOAD_URL" || echo 'Manifest upload failed with status: $?'
    find tasknode_deploy -type f -newer /app/timestamp -not -name 'tasknode_*.log' -not -name 'tasknode_*.tail' -exec cp {} tasknode_generated_files/ \;
    zip -r tasknode_generated_files.zip tasknode_generated_files/
    echo 'Uploading generated files zip...'
    curl -v -H 'Content-Type: application/zip' -T tasknode_generated_files.zip "$ZIP_UPLOAD_URL" || echo 'Zip upload failed with status: $?'
else
    echo 'No new generated files found'
    echo 'Creating empty manifest file...'
    touch ./manifest.txt
    curl -v -H 'Content-Type: text/plain' -T ./manifest.txt "$MANIFEST_UPLOAD_URL" || echo 'Empty manifest upload failed with status: $?'
fi

echo 'Job finished'

# Move exit code check to the end
if [ $SCRIPT_EXIT_CODE -ne 0 ]; then
    echo "Script failed with exit code $SCRIPT_EXIT_CODE"
    exit $SCRIPT_EXIT_CODE
fi