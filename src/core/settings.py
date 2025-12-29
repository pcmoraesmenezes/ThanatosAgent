from dotenv import load_dotenv
import os


class Settings:
    def __init__(self):
        
        load_dotenv()
        
        self.token_telegram = self._safe_load("TOKEN_TELEGRAM")
        
        self.ngrok_url = self._safe_load("NGROK_URL")
        self.groq_api_key = self._safe_load("GROK_API_KEY")
        self.gemini_api_key = self._safe_load("GEMINI_API_KEY")
        
        self.serper_api_key = self._safe_load("SERPER_API_KEY")
        
        self.pg_user = self._safe_load("POSTGRES_USER")
        self.pg_pass = self._safe_load("POSTGRES_PASSWORD")
        self.pg_host = self._safe_load("POSTGRES_HOST")
        self.pg_port = self._safe_load("POSTGRES_PORT")
        self.pg_db = self._safe_load("POSTGRES_DB")
        
        self.context_window = 5000
        
    
    def _safe_load(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Environment variable '{key}' is not set.")
        return value
    
    
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.pg_user}:{self.pg_pass}@{self.pg_host}:{self.pg_port}/{self.pg_db}"

    
    def __str__(self):
        return f"Settings(token_telegram=****, ngrok_url={self.ngrok_url}, groq_api_key=****)"
    
    
settings = Settings()