from pydantic import BaseModel
from typing import Optional


class PriceExtractionResult(BaseModel):
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    is_available: bool = True
    source: str = "UNKNOWN"
    
    @property
    def has_price(self) -> bool:
        return self.current_price is not None and self.current_price > 0