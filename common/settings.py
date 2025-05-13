from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Contains global variables and settings for the server."""

    gemini_api_key: str = ""


settings = Settings()
