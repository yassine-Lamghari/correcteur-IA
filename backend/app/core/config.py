from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "autograde-ocr"
    glm_provider: str = "gradio-space"
    glm_space_url: str = "https://huggingface.co/spaces/prithivMLmods/GLM-OCR-Demo"
    glm_hf_token: str = ""
    translation_default_target: str = "en"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(
        env_prefix="AUTOGRADE_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
