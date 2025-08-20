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
    
    # Database Settings
    postgres_user: str
    postgres_password: str
    postgres_db: str
    
    # JWT Settings
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
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
