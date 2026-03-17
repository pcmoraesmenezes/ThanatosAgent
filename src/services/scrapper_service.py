from typing import List
from bs4 import BeautifulSoup


from src.interface.scrapping_interface import (
    IScrapingStrategy, 
    JsonLdStrategy, 
    AmazonStrategy, 
    MercadoLivreStrategy,
    OpenGraphStrategy
)
from src.domain.product import PriceExtractionResult


class ScraperEngine:
    """
    Orchestrates the price extraction process by trying multiple scraping strategies.
    Supports JSON-LD, Amazon, Mercado Livre, and OpenGraph.
    """
    def __init__(self):
        self.strategies: List[IScrapingStrategy] = [
            JsonLdStrategy(),
            AmazonStrategy(),
            MercadoLivreStrategy(),
            OpenGraphStrategy()
        ]

    def extract_price(self, html: str, url: str) -> PriceExtractionResult:
        """
        Iterates through registered strategies to extract price data from HTML.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        for strategy in self.strategies:
            if strategy.can_handle(url):
                result = strategy.extract(soup)
                
                if result.has_price:
                    return result
        
        return PriceExtractionResult()