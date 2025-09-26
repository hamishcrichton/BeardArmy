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
        )
