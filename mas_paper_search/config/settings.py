from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Define the path to the .env file relative to the config directory
# Assuming .env file will be in the project root (mas_paper_search/)
env_path = Path(__file__).parent.parent / '.env'

class Settings(BaseSettings):
    OPENAI_API_KEY: str = "YOUR_OPENAI_API_KEY_HERE"
    CHROMA_DB_PATH: str = "./chroma_data"  # Default path for local ChromaDB persistence
    CHROMA_COLLECTION_NAME: str = "paper_summaries"
    ARXIV_MAX_RESULTS: int = 10

    model_config = SettingsConfigDict(env_file=env_path, extra='ignore')

settings = Settings()

# Example usage (optional, for testing):
# if __name__ == "__main__":
#     print(f"OpenAI Key: {settings.OPENAI_API_KEY}")
#     print(f"Chroma DB Path: {settings.CHROMA_DB_PATH}")
#     print(f"Chroma Collection: {settings.CHROMA_COLLECTION_NAME}")
