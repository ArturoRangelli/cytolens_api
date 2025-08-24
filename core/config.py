from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    app_name: str = "CytoLens Main Service"
    api_version: str  # From API_VERSION env var (critical for model versioning)
    environment: str = "local"  # "local" or "docker"
    debug: bool = False

    # File Upload Settings
    allowed_slide_extensions: List[str] = [".svs"]
    min_file_size: int = 1024 * 1024  # 1MB
    max_file_size: int = 50 * 1024 * 1024 * 1024  # 50GB

    # AWS Settings
    aws_access_key_id: str
    aws_secret_access_key: str

    # S3 Settings
    s3_bucket_name: str
    s3_slide_folder: str = "slides"
    s3_temp_slide_folder: str = "temp_slides"
    s3_results_folder: str = "results"

    # Local Storage Settings
    slide_dir: str = "/mnt/nvme_gds/slides"
    prediction_dir: str = "/mnt/nvme_gds/predictions"

    # Viewer Settings
    tile_size: int = 512
    tile_overlap: int = 0
    tile_format: str = "jpg"

    # Database Settings
    postgres_user: str
    postgres_password: str
    postgres_db: str

    # JWT Settings
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Inference Service Settings
    inference_service_url: str = "http://localhost:8000"  # URL of inference service
    inference_api_key: str = ""  # API key for inference service

    # Logging Settings
    log_dir: str = "/tmp/cytolens/api_logs"
    log_level: str = "INFO"
    log_rotation_interval: str = "midnight"  # daily rotation at midnight
    log_rotation_count: int = 30  # keep 30 days of logs
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB for error log
    log_backup_count: int = 5  # keep 5 backup files for error log

    @property
    def postgres_host(self) -> str:
        """Database host based on environment"""
        return "postgres" if self.environment == "docker" else "localhost"

    @property
    def database_url(self) -> str:
        """Complete database URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}/{self.postgres_db}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
