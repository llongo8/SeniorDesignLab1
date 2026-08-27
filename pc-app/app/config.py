"""Static configuration, loaded from the environment / .env file.

Anything a user changes at runtime through the web UI lives in settings.py
instead. This module holds only the things that are properties of the machine
the app runs on: where the box is, and how to reach the mail server.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
APP_DIR = PACKAGE_DIR.parent
DATA_DIR = APP_DIR / "data"
STATIC_DIR = APP_DIR / "static"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=APP_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Third box ---
    box_host: str = "192.168.1.50"
    box_port: int = 80
    poll_period_s: float = 1.0
    box_timeout_s: float = 0.8  # must stay well under poll_period_s

    # --- Mail ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_from: str = ""

    @property
    def box_base_url(self) -> str:
        return f"http://{self.box_host}:{self.box_port}"

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)


settings = Settings()
DATA_DIR.mkdir(exist_ok=True)
