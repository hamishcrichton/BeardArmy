from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv


@dataclass(frozen=True)
class Settings:
    youtube_api_key: str
    youtube_channel_id: str | None
    database_url: str | None
    geocoder_provider: str | None
    geocoder_api_key: str | None
    data_dir: str
    # LLM extraction settings
    use_llm_extraction: bool = False
    llm_provider: str | None = None  # "anthropic" or "openai"
    llm_api_key: str | None = None
    llm_model: str | None = None  # Override default model

    @staticmethod
    def load() -> "Settings":
        # Load a .env file from the current working directory or its parents
        load_dotenv(find_dotenv(usecwd=True), override=False)
        return Settings(
            youtube_api_key=os.getenv("YOUTUBE_API_KEY", ""),
            youtube_channel_id=os.getenv("YOUTUBE_CHANNEL_ID"),
            database_url=os.getenv("DATABASE_URL"),
            geocoder_provider=os.getenv("GEOCODER_PROVIDER"),
            geocoder_api_key=os.getenv("GEOCODER_API_KEY"),
            data_dir=os.getenv("DATA_DIR", os.path.abspath(os.path.join(os.getcwd(), "data"))),
            # LLM settings
            use_llm_extraction=os.getenv("USE_LLM_EXTRACTION", "false").lower() in ("true", "1", "yes"),
            llm_provider=os.getenv("LLM_PROVIDER", "anthropic"),
            llm_api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"),
            llm_model=os.getenv("LLM_MODEL"),
        )
