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


def classify_url_pattern(url: str) -> Optional[str]:
    url_lower = url.lower()
    blacklist = [
        'youtube.com', 'instagram.com', 'facebook.com', 
        'login', 'signin', 'cadastro', 'reclameaqui', 'buscacep',
        '/cart', '/checkout', '/minha-conta'
    ]
    if any(x in url_lower for x in blacklist):
        return None

    list_patterns = [
        r'/s\?k=', r'search', r'busca', r'lista', 
        r'/b/', r'category', r'nav', r'\?q=',
        r'shop/', r'promocao', r'ofertas',
        r'/c/', r'/d/', r'/cat/', 
        r'departamento', r'categoria', r'secao', 
        r'colecao', r'linha', r'marcas',
        r'/produtos\?','/todos-os-produtos'
    ]
    
    for pattern in list_patterns:
        if re.search(pattern, url_lower):
            return "OPTION_LIST"

    return "SINGLE_PRODUCT"


async def smart_scrape(client: httpx.AsyncClient, item: dict, engine: ScraperEngine) -> dict:
    if item["type"] == "OPTION_LIST":
        item['final_price'] = "Ver Opções"
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
                item['final_price'] = "Indisponível"
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
                
                list_indicators = ["departamento", "categoria", "produtos", "seleção", "melhores", "loja"]
                
                if any(ind in page_title for ind in list_indicators):
                    item['final_price'] = "Ver Opções"
                else:
                    item['final_price'] = "Ver no Site"
        else:
            item['final_price'] = "Erro Conexão"
            item['is_available'] = False
            
    except Exception as e:
        logger.warning(f"Failed to access {item['link']}: {e}")
        item['final_price'] = "Erro Acesso"
        item['is_available'] = False
        
    return item


@tool
async def search_web_products(query: str) -> str:
    """
    Searches for products on the web using a smart scraping engine.
    """
    logger.info(f"Starting smart search for: {query}")

    local_engine = ScraperEngine()
    
    candidates = []
    async with httpx.AsyncClient() as client:
        headers = {'X-API-KEY': settings.serper_api_key, 'Content-Type': 'application/json'}
        payload = json.dumps({'q': query, 'gl': 'br', 'hl': 'pt-br', 'num': 8}) 
        
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
            final_price = "Ver Opções" if url_type == "OPTION_LIST" else None
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
    for item in candidates:
        if not item.get("is_available", True):
            continue
            
        res = {
            "title": item["title"],
            "url": item["link"],
            "store": item["source"],
            "price": item.get("final_price", "Ver no Site"),
            "original_price": item.get("original_price")
        }
        final_results.append(res)

    final_results.sort(key=lambda x: (
        str(x["price"]) == "Ver no Site",
        str(x["price"]) == "Indisponível",
        str(x["price"]) == "Ver Opções"
    ))

    return json.dumps(final_results[:5], ensure_ascii=False, indent=2)