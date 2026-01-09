from typing import List
from sentence_transformers import SentenceTransformer


from src.core.logger import logger


class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            logger.info("Loading Local Embedding Model (all-MiniLM-L6-v2)...")
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding Model loaded successfully.")
        return cls._instance

    def get_embedding(self, text: str) -> List[float]:

        if not text:
            return [0.0] * 384
            
        try:
            vector = self._model.encode(text).tolist()
            return vector
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * 384


embedding_service = EmbeddingService()