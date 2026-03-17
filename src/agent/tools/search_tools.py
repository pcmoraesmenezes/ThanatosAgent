import json
import httpx
import asyncio

from typing import Optional

from bs4 import BeautifulSoup
import re

from langchain_core.tools import tool

from src.core.settings import settings
from src.core.logger import logger
from src.services.scrapper_service import ScraperEngine
from src.services.catalog_service import CatalogService 


def classify_url_pattern(url: str) -> Optional[str]:
    """
    Classifies a URL into a 'PRODUCT LIST' or 'SINGLE PRODUCT' based on common patterns.
    Stricly excludes non-commercial domains.
    """
    url_lower = url.lower()
    
    strict_blacklist = [
        'wikipedia.org', 'youtube.com', 'reddit.com', 'facebook.com', 
        'instagram.com', 'twitter.com', 'x.com', 'pinterest.com',
        'tiktok.com', 'linkedin.com', 'quora.com', 'medium.com'
    ]
    if any(domain in url_lower for domain in strict_blacklist):
        return None

    blacklist = [
        'login', 'signin', 'signup', 'reclameaqui', 'zip-code',
        '/cart', '/checkout', '/my-account', 'suporte', 'ajuda', 'help'
    ]
    if any(x in url_lower for x in blacklist):
        return None

    list_patterns = [
        r'/s\?k=', r'search', r'query', r'list', 
        r'/b/', r'category', r'nav', r'\?q=',
        r'shop/', r'promo', r'offers', r'oferta',
        r'/c/', r'/d/', r'/cat/', r'vitrine',
        r'department', r'section', r'secao',
        r'collection', r'brand', r'marca',
        r'/products\?', '/all-products', r'todos-os-produtos',
        r'/consoles-e-games/', r'/hardware/', r'/perifericos/',
        r'/espaco-gamer/', r'/gaming-setup/'
    ]
    
    for pattern in list_patterns:
        if re.search(pattern, url_lower):
            return "OPTION_LIST"

    return "SINGLE_PRODUCT"


async def smart_scrape(client: httpx.AsyncClient, item: dict, engine: ScraperEngine) -> dict:
    """
    Attempts to extract structural data from a product page using the scraping engine.
    """
    if item["type"] == "OPTION_LIST":
        item['final_price'] = "See Options"
        item['is_available'] = True
        return item

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml"
        }
        resp = await client.get(item['link'], headers=headers, follow_redirects=True, timeout=10.0)
        
        if resp.status_code == 200:
            price_result = engine.extract_price(resp.text, item['link'])
            
            item['is_available'] = price_result.is_available
            
            if not item['is_available']:
                item['final_price'] = "Out of Stock"
                return item

            curr = price_result.current_price
            old = price_result.original_price

            if curr:
                item['final_price'] = curr
                if old and old > curr:
                    item['original_price'] = old
                item['extraction_method'] = price_result.source 
            else:
                soup = BeautifulSoup(resp.text, 'html.parser')
                page_title = soup.title.get_text().lower() if soup.title else ""
                
                list_indicators = ["department", "category", "products", "selection", "best", "store"]
                
                if any(ind in page_title for ind in list_indicators):
                    item['final_price'] = "See Options"
                else:
                    item['final_price'] = "View on Site"
        else:
            item['final_price'] = "Connection Error"
            item['is_available'] = False
            
    except Exception as e:
        logger.warning(f"Failed to access {item['link']}: {e}")
        item['final_price'] = "Access Error"
        item['is_available'] = False
        
    return item


@tool
async def search_web_products(query: str, gl: str = "us", hl: str = "en") -> str:
    """
    Searches for products on the web. Specify 'gl' (country code, e.g., 'br' or 'us') 
    and 'hl' (language code, e.g., 'pt-br' or 'en') based on the user's intent.
    
    Args:
        query (str): The product search query.
        gl (str): Country code for the search (default: 'us').
        hl (str): Language code for the search (default: 'en').
    """
    logger.info(f"Smart search for: {query} | Market: {gl} | Language: {hl}")

    local_engine = ScraperEngine()
    catalog_service = CatalogService() 
    
    candidates = []
    async with httpx.AsyncClient() as client:
        headers = {'X-API-KEY': settings.serper_api_key, 'Content-Type': 'application/json'}
        payload = json.dumps({'q': query, 'gl': gl, 'hl': hl, 'num': 8}) 
        
        try:
            res = await client.post('https://google.serper.dev/search', headers=headers, data=payload)
            data = res.json()
        except:
            return "Critical error in Search API."

        for item in data.get("shopping", []):
            candidates.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "source": item.get("source", "Shopping"),
                "final_price": item.get("price"), 
                "price_detected": True,
                "type": "SINGLE_PRODUCT",
                "is_available": True 
            })

        for item in data.get("organic", []):
            url_type = classify_url_pattern(item.get("link", ""))
            if url_type is None:
                continue

            final_price = "See Options" if url_type == "OPTION_LIST" else None
            price_detected = True if url_type == "OPTION_LIST" else False

            candidates.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "source": item.get("source", "Web"),
                "final_price": final_price, 
                "price_detected": price_detected,
                "type": url_type or "SINGLE_PRODUCT",
                "is_available": True 
            })

    to_scrape = [c for c in candidates if not c["price_detected"] and c["type"] == "SINGLE_PRODUCT"][:5] 

    if to_scrape:
        logger.info(f"Scraping {len(to_scrape)} URLs using Engine...")
        async with httpx.AsyncClient() as client:
            tasks = [smart_scrape(client, item, local_engine) for item in to_scrape]
            await asyncio.gather(*tasks)

    final_results = []
    save_tasks = []
    
    is_pt = (gl.lower() == 'br')
    currency_symbol = "R$" if is_pt else "$"

    for item in candidates:
        if not item.get("is_available", True):
            continue
            
        price_val = item.get("final_price", "View on Site")
        
        res = {
            "title": item["title"],
            "url": item["link"],
            "store": item["source"],
            "price": price_val,
            "original_price": item.get("original_price")
        }
        final_results.append(res)
        
        if isinstance(price_val, (int, float)) or (isinstance(price_val, str) and currency_symbol in price_val):
            logger.info(f"Auto-saving product: {item['title'][:30]}...")
            save_tasks.append(
                catalog_service.register_product(
                    url=item["link"],
                    title=item["title"],
                    price=price_val,
                    description=f"Auto-saved from search: {query}", 
                    specs={"source": item.get("source")}
                )
            )
    
    if save_tasks:
        try:
            await asyncio.gather(*save_tasks)
            logger.info(f"Successfully auto-saved {len(save_tasks)} products.")
        except Exception as e:
            logger.error(f"Error in auto-save routine: {e}")

    final_results.sort(key=lambda x: (
        str(x["price"]) == "View on Site",
        str(x["price"]) == "Out of Stock",
        str(x["price"]) == "See Options"
    ))

    return json.dumps(final_results[:5], ensure_ascii=False, indent=2)