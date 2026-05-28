from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

PDF_DIR = Path("pdf")
VENUES_DIR = Path("venues")


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db: str
    api_host: str
    api_port: int
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    chat_deployment_name: str
    ieee_xplore_api_key: str


def _load() -> Settings:
    mongo_uri = os.getenv("MONGO_URI", "")
    mongo_db = os.getenv("MONGO_DB", "")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI is required but not set in environment.")
    if not mongo_db:
        raise RuntimeError("MONGO_DB is required but not set in environment.")
    return Settings(
        mongo_uri=mongo_uri,
        mongo_db=mongo_db,
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        chat_deployment_name=os.getenv("CHAT_DEPLOYMENT_NAME", ""),
        ieee_xplore_api_key=os.getenv("IEEE_XPLORE_API_KEY", ""),
    )


settings = _load()
