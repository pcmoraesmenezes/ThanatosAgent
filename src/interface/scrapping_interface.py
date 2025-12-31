from abc import ABC, abstractmethod
from typing import Optional, Dict
from bs4 import BeautifulSoup
import json
import re


from src.utils.scrapping_utils import clean_price_str
from src.domain.product import PriceExtractionResult


class IScrapingStrategy(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        pass

    @abstractmethod
    def extract(self, soup: BeautifulSoup) -> PriceExtractionResult:
        pass


class JsonLdStrategy(IScrapingStrategy):
    def can_handle(self, url: str) -> bool:
        return True 

    def extract(self, soup: BeautifulSoup) -> PriceExtractionResult:
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                if not script.string: continue
                data = json.loads(script.string)
                
                if isinstance(data, list) and data: data = data[0]
                
                if isinstance(data, dict) and 'offers' in data:
                    offers = data['offers']
                    if isinstance(offers, list) and offers: offer = offers[0]
                    elif isinstance(offers, dict): offer = offers
                    else: continue
                    
                    availability = offer.get('availability', '')
                    is_available = True
                    if 'outofstock' in availability.lower() or 'soldout' in availability.lower():
                        is_available = False

                    price = offer.get('price') or offer.get('lowPrice')
                    if price:
                        c_price = float(price)
                        o_price = None
                        if offer.get('highPrice'): 
                            o_price = float(offer['highPrice'])
                            
                        return PriceExtractionResult(
                            current_price=c_price,
                            original_price=o_price,
                            is_available=is_available,
                            source="JSON_LD"
                        )
            except:
                continue
        
        return PriceExtractionResult()


class AmazonStrategy(IScrapingStrategy):
    def can_handle(self, url: str) -> bool:
        return "amazon" in url.lower()

    def extract(self, soup: BeautifulSoup) -> PriceExtractionResult:
        c_price = None
        o_price = None
        is_available = True

        availability_div = soup.select_one('#availability')
        page_text = soup.get_text().lower()
        
        if availability_div:
            text = availability_div.get_text().lower()
            if "indisponível" in text or "não disponível" in text:
                is_available = False
        elif "atualmente indisponível" in page_text:
            is_available = False

        if not is_available:
            return PriceExtractionResult(is_available=False, source="AMAZON_HTML")

        curr = soup.select_one('.a-price:not(.a-text-price) .a-offscreen')
        if curr: c_price = clean_price_str(curr.get_text())
        
        old = soup.select_one('.a-price.a-text-price .a-offscreen')
        if old: o_price = clean_price_str(old.get_text())
        
        return PriceExtractionResult(
            current_price=c_price,
            original_price=o_price,
            is_available=True,
            source="AMAZON_HTML"
        )


class MercadoLivreStrategy(IScrapingStrategy):
    def can_handle(self, url: str) -> bool:
        return "mercadolivre" in url.lower()

    def extract(self, soup: BeautifulSoup) -> PriceExtractionResult:
        c_price = None
        o_price = None
        is_available = True
        
        header = soup.select_one('.ui-pdp-header__title-container') 
        if soup.find(string=re.compile("Anúncio pausado|Finalizado", re.IGNORECASE)):
             is_available = False

        if not is_available:
             return PriceExtractionResult(is_available=False, source="ML_HTML")

        price_container = soup.select_one('.ui-pdp-price__main-container')
        if price_container:
            curr = price_container.select_one('.andes-money-amount__fraction')
            if curr: c_price = clean_price_str(curr.get_text())
            
            old_container = price_container.select_one('.ui-pdp-price__original-value')
            if old_container:
                old_val = old_container.select_one('.andes-money-amount__fraction')
                if old_val: o_price = clean_price_str(old_val.get_text())
                
        return PriceExtractionResult(
            current_price=c_price,
            original_price=o_price,
            is_available=True,
            source="ML_HTML"
        )


class OpenGraphStrategy(IScrapingStrategy):
    def can_handle(self, url: str) -> bool:
        return True

    def extract(self, soup: BeautifulSoup) -> PriceExtractionResult:
        c_price = None
        og_price = soup.find("meta", property="product:price:amount")
        
        
        if og_price:
            try:
                c_price = float(og_price["content"])
            except:
                pass
                
        return PriceExtractionResult(
            current_price=c_price,
            is_available=True,
            source="OPEN_GRAPH"
        )