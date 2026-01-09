import httpx

from langchain_core.tools import tool


from src.services.scrapper_service import ScraperEngine
from src.core.logger import logger



@tool
async def check_price_from_url(url: str) -> str:
    """
    Extracts the current price and availability from a SPECIFIC URL.
    Use this tool when the user provides a direct link or when you need 
    to confirm the price of a specific candidate found in a search.

    Args:
        url (str): The full URL of the product page (Amazon, Mercado Livre, etc).

    Returns:
        str: A formatted string with 'price', 'original_price', and 'source'.
    """
    logger.info(f"Sniper check on: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml"
    }

    engine = ScraperEngine()
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, follow_redirects=True, timeout=12.0)
            
            if resp.status_code != 200:
                logger.warning(f"Failed to access URL: {resp.status_code}")
                return f"Error: HTTP {resp.status_code}"
            
            result = engine.extract_price(resp.text, url)
            
            if not result.is_available:
                return "Status: Indisponível/Esgotado"
            
            if result.has_price:
                return (
                    f"Price: R$ {result.current_price:.2f} | "
                    f"Original: {result.original_price or 'N/A'} | "
                    f"Source: {result.source}"
                )
            
            return "Could not extract price. Structure might have changed or site is not supported."

    except Exception as e:
        logger.error(f"Sniper error processing {url}: {e}")
        return f"Connection Failed: {str(e)}"