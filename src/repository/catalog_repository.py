import json


from sqlalchemy import text
from typing import List, Dict, Optional, Any
from decimal import Decimal

from src.interface.catalog_interface import ICatalogRepository
from src.core.database import db_manager
from src.core.logger import logger


class CatalogRepository(ICatalogRepository):
    
    async def search_full_text(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        sql = text("""
            SELECT 
                product_id, title, url, price_amount, currency, description
            FROM products p
            JOIN LATERAL (
                SELECT price_amount, currency 
                FROM price_history ph 
                WHERE ph.product_id = p.product_id 
                ORDER BY scraped_at DESC LIMIT 1
            ) latest_price ON true
            WHERE search_vector @@ websearch_to_tsquery('portuguese', :q)
            ORDER BY ts_rank(search_vector, websearch_to_tsquery('portuguese', :q)) DESC
            LIMIT :limit;
        """)
        
        async with await db_manager.get_session() as session:
            result = await session.execute(sql, {"q": query, "limit": limit})
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def upsert_product_and_price(self, 
                                       url: str, 
                                       domain: str, 
                                       title: str, 
                                       price: Optional[Decimal],
                                       specs: Dict,
                                       description: Optional[str] = None) -> str:

        sql_product = text("""
            INSERT INTO products (url, domain, title, description, specs)
            VALUES (:url, :domain, :title, :desc, :specs)
            ON CONFLICT (url) DO UPDATE 
            SET title = EXCLUDED.title,
                last_updated_at = NOW()
            RETURNING product_id;
        """)

        sql_price = text("""
            INSERT INTO price_history (product_id, price_amount)
            VALUES (:pid, :price);
        """)

        async with await db_manager.get_session() as session:
            async with session.begin():
                result = await session.execute(sql_product, {
                    "url": url,
                    "domain": domain,
                    "title": title,
                    "desc": description,
                    "specs": json.dumps(specs)
                })
                product_id = result.scalar()

                if price is not None:
                    await session.execute(sql_price, {
                        "pid": product_id,
                        "price": price
                    })
                else:
                    logger.warning(f"Product registered without price: {title}")
                
        return str(product_id)