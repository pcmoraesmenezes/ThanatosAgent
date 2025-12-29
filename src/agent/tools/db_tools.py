from langchain_core.tools import tool


from src.services.catalog_service import CatalogService


catalog_service = CatalogService()


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
    return str(results)


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