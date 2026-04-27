from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str
    output_dir: str = "output"
    max_concurrent_requests: int = 5
    gemini_model: str = "gemini-3.1-flash-lite-preview"

    model_config = {"env_file": str(Path(__file__).parent.parent.parent / ".env")}


settings = Settings()
