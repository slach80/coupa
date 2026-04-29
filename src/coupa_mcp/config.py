import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    api_url: str
    api_key: str


def load_config() -> Config:
    api_url = os.environ.get("COUPA_API_URL", "").rstrip("/")
    api_key = os.environ.get("COUPA_API_KEY", "")
    if not api_url:
        raise RuntimeError("COUPA_API_URL environment variable is required")
    if not api_key:
        raise RuntimeError("COUPA_API_KEY environment variable is required")
    return Config(api_url=api_url, api_key=api_key)
