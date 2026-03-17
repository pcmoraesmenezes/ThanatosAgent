from langchain_core.tools import tool


from src.services.catalog_service import CatalogService


catalog_service = CatalogService()


def _format_product_context(products: list) -> str:
    """
    Formats a list of product records into a readable string context for the LLM.
    """
    context_list = []
    
    for product in products:
        price = float(product.get('price_amount') or 0)
        pct_change = float(product.get('price_change_percent') or 0)
        low_30d = float(product.get('lowest_price_30d') or 0)
        
        trend_msg = "Stable"

        if pct_change < -1.0:
            trend_msg = f"PRICE DROP! Down {abs(pct_change)}% (Was $ {product.get('previous_price')})"

        elif pct_change > 1.0:
            trend_msg = f"PRICE INCREASE! Up {pct_change}% (Was $ {product.get('previous_price')})"
            
        is_good_deal = price <= low_30d
        deal_tag = '[BEST PRICE IN 30 DAYS]' if is_good_deal and price > 0 else ""
        
        item = {
            "title": product['title'],
            'current_price': f'$ {price:.2f}',
            'trend': trend_msg,
            'analysis': deal_tag,
            'url': product['url']
        }      
        
        context_list.append(item)
        
    return str(context_list)


@tool
async def check_local_database(query: str) -> str:
    """
    Queries the internal product database/catalog.

    MANDATORY: This tool MUST be used FIRST for any product search request
    before attempting to scrape external websites. It checks if the information
    already exists locally to save resources.

    Args:
        query (str): The search term or product name to look up.

    Returns:
        str: A string representation of the found products or a message indicating
             no results were found.
    """
    results = await catalog_service.search_products(query)
    if not results:
        return "No results found in the local database."
    return _format_product_context(results)


@tool
async def save_product_memory(url: str, title: str, price: float, description: str = "") -> str:
    """
    Persists a specific product into the internal database.

    Use this tool to save the best offers found during a search or when the
    user explicitly requests to track a product.

    Args:
        url (str): The direct link to the product page.
        title (str): The name/title of the product.
        price (float): The detected price of the product.
        description (str, optional): A brief description or metadata. Defaults to "".

    Returns:
        str: A confirmation message with the Product ID or an error message.
    """
    try:
        pid = await catalog_service.register_product(
            url=url,
            title=title,
            price=price,
            description=description
        )
        return f"Product saved successfully! ID: {pid}"
    except Exception as e:
        return f"Error saving product: {str(e)}"