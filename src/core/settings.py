from dotenv import load_dotenv
import os


class Settings:
    def __init__(self):
        
        load_dotenv()
        
        self.token_telegram = self._safe_load("TOKEN_TELEGRAM")
        self.ngrok_url = self._safe_load("NGROK_URL")
        self.groq_api_key = self._safe_load("GROK_API_KEY")
    
    def _safe_load(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Environment variable '{key}' is not set.")
        return value
    
    
    def __str__(self):
        return f"Settings(token_telegram=****, ngrok_url={self.ngrok_url}, groq_api_key=****)"
    
    
settings = Settings()