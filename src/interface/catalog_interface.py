from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from decimal import Decimal

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
                                       description: Optional[str] = None,
                                       embedding: Optional[List[float]] = None
    ) -> str:
        pass
    
    
    @abstractmethod
    async def get_average_price_last_30_days(self, product_id: str) -> Optional[Decimal]:
        pass
    
    
    @abstractmethod
    async def search_hybrid(self, query_text: str, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        pass