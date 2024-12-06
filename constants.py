from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(Enum):
    OUTPUT_LOG = "output_log"
    ERROR_LOG = "error_log"
    GENERATED = "generated"
    ZIPPED_GENERATED = "zipped_generated"


MAX_IN_PROGRESS = 4
