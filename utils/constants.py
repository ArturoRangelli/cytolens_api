import os

from cachetools import LRUCache

# Secret
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

# AWS
AWS_REGION = ""
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_SLIDE_FOLDER = "slides"
S3_RESULTS_FOLDER = "results"
S3_TEMP_SLIDE_FOLDER = "temp_slides"

# Postgres
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# WSI-Slides
SLIDE_INFO_CACHE = LRUCache(maxsize=8)
TILE_SIZE = 512  # 256 before
OVERLAP = 0
SLIDE_DIR = "/mnt/nvme_gds/slides"
PREDICTION_DIR = "/mnt/nvme_gds/predictions"
TILE_FMT = "jpg"

ALLOWED_SLIDES = [".svs"]
APP_ENV = os.environ.get("APP_ENV")
