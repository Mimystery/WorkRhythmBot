from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    admin_id: int = Field(..., alias="ADMIN_ID")

    # Render gives a single DATABASE_URL; local dev uses separate fields
    database_url_raw: str | None = Field(None, alias="DATABASE_URL")
    db_user: str = Field("postgres", alias="DB_USER")
    db_pass: str = Field("", alias="DB_PASS")
    db_host: str = Field("localhost", alias="DB_HOST")
    db_port: int = Field(5432, alias="DB_PORT")
    db_name: str = Field("workflow", alias="DB_NAME")

    @property
    def database_url(self) -> str:
        if self.database_url_raw:
            url = self.database_url_raw
            # Render gives postgresql://, asyncpg needs postgresql+asyncpg://
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
