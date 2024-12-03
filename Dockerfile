ARG TARGETPLATFORM=linux/amd64
FROM --platform=$TARGETPLATFORM python:3.12-slim

# Copy the entrypoint script into the image
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set the working directory
WORKDIR /app

# Use the script as the entrypoint
CMD ["/app/entrypoint.sh"]