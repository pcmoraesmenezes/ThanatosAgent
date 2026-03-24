import json


from sqlalchemy import text
from typing import List, Dict, Optional, Any
from decimal import Decimal

from src.interface.catalog_interface import ICatalogRepository
from src.core.database import db_manager
from src.core.logger import logger


class CatalogRepository(ICatalogRepository):
    """
    Handles persistence and retrieval of products and price history from the database.
    Implements a hybrid search using both full-text and vector-based methods.
    """
    
    async def search_full_text(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Performs a full-text search on the product catalog using PostgreSQL's tsvector.
        """
        sql = text("""
            SELECT
                product_id,
                title,
                url,
                description,
                current_price as price_amount,
                previous_price,
                price_change_percent,
                lowest_price_30d
            FROM products
            WHERE search_vector @@ websearch_to_tsquery('portuguese', :q)
            AND is_active = TRUE
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
                                       description: Optional[str] = None,
                                       embedding: Optional[List[float]] = None) -> str: 
        """
        Inserts or updates a product and its current price.
        If the product exists, updates its metadata. Always adds a new record to price history.
        """
        sql_product = text("""
            INSERT INTO products (url, domain, title, description, specs, embedding, is_active)
            VALUES (:url, :domain, :title, :desc, :specs, :embedding, TRUE)
            ON CONFLICT (url) DO UPDATE 
            SET title = EXCLUDED.title,
                description = EXCLUDED.description,
                specs = EXCLUDED.specs,
                embedding = EXCLUDED.embedding,
                last_updated_at = NOW(),
                is_active = TRUE
            RETURNING product_id;
        """)

        sql_price = text("""
            INSERT INTO price_history (product_id, price_amount)
            VALUES (:pid, :price);
        """)
        
        embedding_val = str(embedding) if embedding else None

        async with await db_manager.get_session() as session:
            async with session.begin():
                result = await session.execute(sql_product, {
                    "url": url,
                    "domain": domain,
                    "title": title,
                    "desc": description,
                    "specs": json.dumps(specs),
                    "embedding": embedding_val 
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
    
    async def get_average_price_last_30_days(self, product_id: str) -> Optional[Decimal]:
        """
        Calculates the average price of a product over the last 30 days.
        """
        sql = text(
            """
                SELECT AVG(price_amount)
                FROM price_history
                WHERE product_id = :pid
                AND scraped_at >=NOW() - INTERVAL '30 days'
                AND scraped_at < NOW() - INTERVAL '1 minute';
            """
        )
        
        async with await db_manager.get_session() as session:
            result = await session.execute(sql, {"pid": product_id})
            avg_price = result.scalar()
            
            if avg_price:
                return Decimal(avg_price)
            return None
        
    async def search_hybrid(self, query_text: str, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Performs a hybrid search (Text + Vector) using Reciprocal Rank Fusion (RRF).
        Uses a 384-dimension local embedding vector.
        """
        sql = text("""
            WITH semantic_search AS (
                SELECT 
                    product_id, 
                    1.0 / (ROW_NUMBER() OVER (ORDER BY embedding <=> :embedding) + 60) AS score_vec
                FROM products
                WHERE is_active = TRUE
                ORDER BY embedding <=> :embedding
                LIMIT 20
            ),
            keyword_search AS (
                SELECT 
                    product_id, 
                    1.0 / (ROW_NUMBER() OVER (ORDER BY ts_rank(search_vector, websearch_to_tsquery('portuguese', :q)) DESC) + 60) AS score_text
                FROM products
                WHERE search_vector @@ websearch_to_tsquery('portuguese', :q)
                AND is_active = TRUE
                LIMIT 20
            )
            SELECT 
                p.product_id, 
                p.title, 
                p.url, 
                p.description,
                p.current_price as price_amount,
                p.previous_price,
                p.price_change_percent,
                p.lowest_price_30d,
                (COALESCE(s.score_vec, 0.0) + COALESCE(k.score_text, 0.0)) AS final_score
            FROM products p
            LEFT JOIN semantic_search s ON p.product_id = s.product_id
            LEFT JOIN keyword_search k ON p.product_id = k.product_id
            WHERE (COALESCE(s.score_vec, 0.0) + COALESCE(k.score_text, 0.0)) > 0
            ORDER BY final_score DESC
            LIMIT :limit;
        """)

        async with await db_manager.get_session() as session:
            result = await session.execute(sql, {
                "q": query_text, 
                "embedding": str(query_vector), 
                "limit": limit
            })
            rows = result.mappings().all()
            return [dict(row) for row in rows]