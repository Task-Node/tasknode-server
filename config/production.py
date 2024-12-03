import os

from .default import Default


class Production(Default):
    ENV: str = "Production"

    # # Note: Serverless adds /prd to the root path when you deploy to prd, so you need to set that here
    # # unless using a custom domain.
    # ROOT_PATH: str = "/prd"

    # s3
    FILE_DROP_BUCKET: str = "tasknode-file-drop-prd"
    PROCESSED_FILES_BUCKET: str = "tasknode-processed-files-prd"

    CUSTOM_DOMAIN: str = "api.tasknode.xyz"

    # ecs
    ECS_CLUSTER: str = os.environ.get("ECS_CLUSTER", "TASKNODE-CLUSTER-PRD")
    ECS_TASK_EXECUTION_ROLE: str = os.environ.get("ECS_TASK_EXECUTION_ROLE", "TASKNODE-TASK-EXECUTION-ROLE-PRD")
