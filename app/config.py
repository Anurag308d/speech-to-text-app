from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    database_url: str = ""
    groq_stt_model: str = "whisper-large-v3"
    tts_voice_en: str = "en_US-lessac-medium"
    tts_voice_hi: str = "hi_IN-pratham-medium"

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url.strip()
        if not url:
            return "sqlite:///./speechapp.db"
        # Railway and Heroku style URLs start with postgres://, SQLAlchemy wants postgresql://
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return url


settings = Settings()
