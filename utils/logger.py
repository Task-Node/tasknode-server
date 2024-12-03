import logging

# Configure logging for Lambda environment
logger = logging.getLogger()  # Get root logger instead of __name__
logger.setLevel(logging.INFO)

# Clear any existing handlers to avoid duplicate logs
logger.handlers = []

# Add stdout handler
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(handler)