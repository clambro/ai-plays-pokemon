"""Application settings loaded from the environment."""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Contains keys read from the environment."""

    openai_api_key: str
    logfire_token: str = ""


settings = Settings()
