from typing import List, Dict, Optional
from urllib.parse import urlparse

from src.interface.catalog_interface import ICatalogRepository
from src.repository.catalog_repository import CatalogRepository


class CatalogService:
    def __init__(self, repository: ICatalogRepository = None):
        self.repository = repository or CatalogRepository()    
    
    async def search_products(self, query: str) -> List[Dict]:
        return await self.repository.search_full_text(query)


    async def register_product(self, 
                             url: str, 
                             title: str, 
                             price: float, 
                             description: str = "",
                             specs: dict = {}) -> str:
        
        try:
            domain = urlparse(url).netloc
        except:
            domain = "unknown"

        return await self.repository.upsert_product_and_price(
            url=url,
            domain=domain,
            title=title,
            price=price,
            specs=specs,
            description=description
        )