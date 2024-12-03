# Use the linux/amd64 version of the python image (for AWS Fargate)
FROM --platform=linux/amd64 python:3.12-slim

# Copy the entrypoint script into the image
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set the working directory
WORKDIR /app

# Use the script as the entrypoint
CMD ["/app/entrypoint.sh"]