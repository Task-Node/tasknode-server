import json
import os
from config import get_settings

env = os.environ.get("env", "dev").lower()  # default to dev
settings = get_settings(env)

f = open(f"serverless_config_{env}.json", "w")
json.dump(settings.dict(), f)
f.close()
