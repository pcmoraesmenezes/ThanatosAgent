import json
import httpx
import asyncio
import re
from typing import Optional
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from src.core.settings import settings
from src.core.logger import logger


def classify_url_pattern(url: str) -> Optional[str]:
    """
    Classifies the type of item based on the URL structure using heuristics.

    Args:
        url (str): The URL to analyze.

    Returns:
        Optional[str]: 'SINGLE_PRODUCT', 'OPTION_LIST', or None if the URL is blacklisted.
    """
    url_lower = url.lower()
    
    blacklist = [
        'youtube.com', 'instagram.com', 'facebook.com', 
        'login', 'signin', 'cadastro', 'reclameaqui', 'buscacep'
    ]
    if any(x in url_lower for x in blacklist):
        return None

    product_patterns = [r'/dp/', r'/p/', r'/produto/', r'/imb/', r'/item/']
    for pattern in product_patterns:
        if re.search(pattern, url_lower):
            return "SINGLE_PRODUCT"

    list_patterns = [r'search', r'busca', r'lista', r'/b/', r'category', r'nav', r'\?q=']
    for pattern in list_patterns:
        if re.search(pattern, url_lower):
            return "OPTION_LIST"

    return "SINGLE_PRODUCT"



def extract_real_price(html_content: str, source: str) -> Optional[str]:
    """
    Extracts the product price using a reliability hierarchy.
    
    Strategy:
    1. JSON-LD (Schema.org): Hidden structured data (Highest reliability).
    2. Meta Tags (OpenGraph): Social media metadata.
    3. CSS Selectors: Visual HTML elements (Lowest reliability, fallback).

    Args:
        html_content (str): The raw HTML of the page.
        source (str): The source domain name (e.g., 'Amazon', 'MercadoLivre') for specific CSS rules.

    Returns:
        Optional[str]: The detected price formatted as a string (e.g., "R$ 50.00"), or None.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                if not script.string: continue
                data = json.loads(script.string)
                
                if isinstance(data, list): 
                    if not data: continue
                    data = data[0]
                
                if isinstance(data, dict) and 'offers' in data:
                    offers = data['offers']
                    price = None
                    if isinstance(offers, list) and len(offers) > 0:
                        price = offers[0].get('price') or offers[0].get('lowPrice')
                    elif isinstance(offers, dict):
                        price = offers.get('price') or offers.get('lowPrice')
                    
                    if price: return f"R$ {price}"
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue


        meta_selectors = [
            {"property": "product:price:amount"},
            {"property": "og:price:amount"},
            {"name": "twitter:data1"}
        ]
        
        for selector in meta_selectors:
            tag = soup.find("meta", attrs=selector)
            if tag and tag.get("content"):
                return f"R$ {tag['content']}"

        src_lower = source.lower()
        
        if "amazon" in src_lower:
            price_tag = soup.find(name="span", attrs={"class": "a-offscreen"}) 
            if price_tag: return price_tag.get_text(strip=True)

        if "mercadolivre" in src_lower:
            price_tag = soup.find(name="span", attrs={"class": "andes-money-amount__fraction"})
            if price_tag: return f"R$ {price_tag.get_text(strip=True)}"
        
        if "magazineluiza" in src_lower or "magalu" in src_lower:
            price_tag = soup.find(name="p", attrs={"data-testid": "price-value"})
            if price_tag: return price_tag.get_text(strip=True)

    except Exception as e:
        logger.error(f"BS4 Parser Error: {e}")
        pass
        
    return None


async def smart_scrape(client: httpx.AsyncClient, item: dict) -> dict:
    """
    Decides whether to scrape a URL and executes the surgical extraction if necessary.

    Args:
        client (httpx.AsyncClient): The async HTTP client.
        item (dict): The product candidate dictionary.

    Returns:
        dict: The updated item dictionary with 'final_price' and 'extraction_method'.
    """
    if item.get("price_detected") or item["type"] == "OPTION_LIST":
        return item

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        resp = await client.get(item['link'], headers=headers, follow_redirects=True, timeout=8.0)
        
        if resp.status_code == 200:
            extracted_price = extract_real_price(resp.text, item.get('source', ''))
            
            if extracted_price:
                item['final_price'] = extracted_price
                item['extraction_method'] = "SCRAPED_STRUCTURED"
            else:
                item['final_price'] = "See on Site"
                item['extraction_method'] = "NOT_FOUND"
        else:
            item['final_price'] = "Connection Error"
            
    except Exception as e:
        logger.warning(f"Failed to access {item['link']}: {e}")
        item['final_price'] = "Connection Error"
        
    return item



@tool
async def search_web_products(query: str) -> str:
    """
    Searches for products on the web, prioritizing API data and performing surgical scraping when necessary.

    This tool orchestrates the following flow:
    1. Fetches data from Google Search/Shopping via Serper API.
    2. Prioritizes structured data from Google Shopping.
    3. Analyzes organic results and scrapes structured data (JSON-LD) only if the price is missing.

    Args:
        query (str): The product search query (e.g., 'playstation 5 controller').

    Returns:
        str: A JSON string containing the top relevant products with their prices and links.
    """
    logger.info(f"Starting smart search for: {query}")
    
    candidates = []
    async with httpx.AsyncClient() as client:
        headers = {'X-API-KEY': settings.serper_api_key, 'Content-Type': 'application/json'}
        payload = json.dumps({'q': query, 'gl': 'br', 'hl': 'pt-br', 'num': 10})
        
        try:
            res = await client.post('https://google.serper.dev/search', headers=headers, data=payload)
            data = res.json()
        except Exception:
            return "Critical error in Search API."

        for item in data.get("shopping", []):
            candidates.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "source": item.get("source", "Shopping"),
                "final_price": item.get("price"), 
                "price_detected": True,
                "type": "SINGLE_PRODUCT",
                "extraction_method": "API_SERPER"
            })

        for item in data.get("organic", []):
            url_type = classify_url_pattern(item.get("link", ""))
            if not url_type: continue 
            
            snippet_price = None
            if item.get("price"):
                snippet_price = item.get("price")
            elif "R$" in item.get("snippet", ""):
                 match = re.search(r'R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', item.get("snippet", ""))
                 if match: snippet_price = f"R$ {match.group(1)}"

            candidates.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "source": item.get("source", "Web"),
                "final_price": snippet_price, 
                "price_detected": snippet_price is not None,
                "type": url_type,
                "extraction_method": "SNIPPET" if snippet_price else "PENDING"
            })

    if not candidates:
        return "No products found."

    to_scrape = [
        c for c in candidates 
        if c["type"] == "SINGLE_PRODUCT" 
        and not c["price_detected"]
    ]
    to_scrape = to_scrape[:5] 

    if to_scrape:
        logger.info(f"Starting surgical scraping on {len(to_scrape)} URLs...")
        async with httpx.AsyncClient() as client:
            tasks = [smart_scrape(client, item) for item in to_scrape]
            await asyncio.gather(*tasks)

    final_results = []
    for item in candidates:
        price = item.get("final_price")
        
        if not price and item["type"] == "OPTION_LIST":
            price = "Various Options"
        elif not price or price == "Connection Error":
            price = "See on Site"

        final_results.append({
            "title": item["title"],
            "url": item["link"],
            "store": item["source"],
            "price": price,
            "type": item["type"],
            "extraction_method": item.get("extraction_method", "UNKNOWN")
        })


    final_results.sort(key=lambda x: (
        x["price"] == "See on Site", 
        x["type"] == "OPTION_LIST"
    ))

    return json.dumps(final_results[:6], ensure_ascii=False, indent=2)