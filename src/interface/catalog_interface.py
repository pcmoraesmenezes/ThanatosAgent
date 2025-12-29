from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

class ICatalogRepository(ABC):
    
    @abstractmethod
    async def search_full_text(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca produtos via Full-Text Search no DB."""
        pass

    @abstractmethod
    async def upsert_product_and_price(self, 
                                       url: str, 
                                       domain: str, 
                                       title: str, 
                                       price: float, 
                                       specs: Dict,
                                       description: Optional[str] = None) -> str:
        """Insere ou atualiza produto e registra histórico de preço."""
        pass