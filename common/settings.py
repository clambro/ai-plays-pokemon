from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Contains keys read from the environment."""

    gemini_api_key: str = ""
    junjo_server_api_key: str = ""


settings = Settings()
