from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "whatsapp-ai-assistant"
    database_url: str = "postgresql+psycopg://assistant:assistant@localhost:5432/assistant"
    redis_url: str = "redis://localhost:6379/0"
    whatsapp_access_token: SecretStr = SecretStr("")
    whatsapp_app_secret: SecretStr = SecretStr("")
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: SecretStr = SecretStr("")
    whatsapp_api_version: str = "v26.0"
    ai_provider: Literal["ollama", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    max_input_chars: int = Field(default=12_000, ge=100, le=50_000)
    max_output_tokens: int = Field(default=400, ge=1, le=4_096)
    max_context_chars: int = Field(default=16_000, ge=500, le=100_000)
    requests_per_minute: int = Field(default=20, ge=1, le=10_000)
    admin_api_token: SecretStr = SecretStr("")
    enable_dev_simulator: bool = False
    conversation_history_limit: int = Field(default=12, ge=1, le=100)
    memory_limit: int = Field(default=10, ge=1, le=100)
    app_timezone: str = "Asia/Kathmandu"
    message_retention_days: int = Field(default=30, ge=1, le=3650)

    @model_validator(mode="after")
    def require_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            required = {
                "WHATSAPP_VERIFY_TOKEN": self.whatsapp_verify_token,
                "WHATSAPP_APP_SECRET": self.whatsapp_app_secret,
                "WHATSAPP_ACCESS_TOKEN": self.whatsapp_access_token,
                "ADMIN_API_TOKEN": self.admin_api_token,
            }
            missing = [
                name
                for name, value in required.items()
                if not (value.get_secret_value() if isinstance(value, SecretStr) else value)
            ]
            if missing:
                raise ValueError("Missing production configuration: " + ", ".join(missing))
        if self.ai_provider == "openai" and not self.openai_api_key.get_secret_value():
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
