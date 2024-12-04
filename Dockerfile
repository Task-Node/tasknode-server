ARG TARGETPLATFORM=linux/amd64
FROM --platform=$TARGETPLATFORM python:3.12-slim

# Install Jupyter dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    unzip \
    curl \
    zip \
    jq \
    file \
    && pip3 install jupyter nbconvert ipykernel \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the entrypoint script into the image
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set the working directory
WORKDIR /app

# Use the script as the entrypoint
CMD ["/app/entrypoint.sh"]