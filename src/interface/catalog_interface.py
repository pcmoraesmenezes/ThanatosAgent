from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

class ICatalogRepository(ABC):
    
    @abstractmethod
    async def search_full_text(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def upsert_product_and_price(self, 
                                       url: str, 
                                       domain: str, 
                                       title: str, 
                                       price: Optional[float],
                                       specs: Dict,
                                       description: Optional[str] = None) -> str:
        pass