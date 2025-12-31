from typing import List, Dict, Optional
from urllib.parse import urlparse
from decimal import Decimal, InvalidOperation

from src.interface.catalog_interface import ICatalogRepository
from src.repository.catalog_repository import CatalogRepository
from src.core.logger import logger


class CatalogService:
    def __init__(self, repository: ICatalogRepository = None):
        self.repository = repository or CatalogRepository()    
    
    async def search_products(self, query: str) -> List[Dict]:
        return await self.repository.search_full_text(query)

    def _sanitize_price(self, price: float | str) -> Optional[Decimal]:
        if isinstance(price, (float, int)):
            return Decimal(str(price))
        
        if isinstance(price, str):
            clean = price.replace("R$", "").replace(" ", "").replace("\xa0", "")
            
            if "," in clean:
                clean = clean.replace(".", "").replace(",", ".")
            
            try:
                val = Decimal(clean)
                return val if val > 0 else None 
            except InvalidOperation:
                logger.error(f"Failed to convert price: {price}")
                return None
        
        return None

    async def register_product(self, 
                             url: str, 
                             title: str, 
                             price: float | str, 
                             description: str = "",
                             specs: dict = {}) -> str:
        
        try:
            domain = urlparse(url).netloc
        except:
            domain = "unknown"

        final_price = self._sanitize_price(price)

        return await self.repository.upsert_product_and_price(
            url=url,
            domain=domain,
            title=title,
            price=final_price, 
            specs=specs,
            description=description
        )
