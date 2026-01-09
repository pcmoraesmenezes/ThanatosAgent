from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
from decimal import Decimal, InvalidOperation, getcontext

from src.interface.catalog_interface import ICatalogRepository
from src.repository.catalog_repository import CatalogRepository
from src.services.embedding_service import embedding_service
from src.core.logger import logger


class CatalogService:
    def __init__(self, repository: ICatalogRepository = None):
        self.repository = repository or CatalogRepository()    
        getcontext().prec = 6
    
    async def search_products(self, query: str) -> List[Dict]:
        vector = embedding_service.get_embedding(query)
        
        return await self.repository.search_hybrid(query_text=query, query_vector=vector)
    
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
        
        text_to_embed = f"{title}. {description or ''}"
        
        vector = embedding_service.get_embedding(text_to_embed)

        return await self.repository.upsert_product_and_price(
            url=url,
            domain=domain,
            title=title,
            price=final_price, 
            specs=specs,
            description=description,
            embedding=vector 
        )


    async def calculate_real_discount(self, product_id: str, current_price: Decimal | float) -> Dict[str, Any]:
        if not isinstance(current_price, Decimal):
            try:
                current_price = Decimal(str(current_price))
            except:
                return {"error": "invalid price format"}
            
            
        sum_30d = await self.repository.get_average_price_last_30_days(product_id=product_id)
        
        if not sum_30d or sum_30d == 0:
            return {
                "real_discount_percent": 0,
                "is_real_offer": False,
                "message": "Unsuficient history to statistical analysis",
                "sum_30d": None
            }
            
        
        discount_ratio = Decimal(1) - (current_price / sum_30d)
        discount_percent = discount_ratio * 100
        
        is_real_offer = discount_ratio > 15
        
        status_msg = ""
        
        if is_real_offer:
            status_msg = f'Real offer!: {discount_percent:.1f}% below of mean from previous 30 days'
            
        elif discount_percent > 0:
            status_msg = f'Shiny discount. {discount_percent:.1f}% Inside standard desviation'    
            
        else:
            status_msg = "beware! inflact price"
            
        return {
            "real_discount_percent": round(float(discount_percent), 2),
            "is_real_offer": is_real_offer,
            "message": status_msg,
            "sum_30d": round(float(sum_30d), 2),
            "current_price": round(float(current_price), 2)
        }
        