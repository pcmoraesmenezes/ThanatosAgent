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
                                       description: Optional[str] = None,
                                       embedding: Optional[List[float]] = None) -> str: 

        sql_product = text("""
            INSERT INTO products (url, domain, title, description, specs, embedding, is_active)
            VALUES (:url, :domain, :title, :desc, :specs, :embedding, TRUE)
            ON CONFLICT (url) DO UPDATE 
            SET title = EXCLUDED.title,
                description = EXCLUDED.description,
                specs = EXCLUDED.specs,
                embedding = EXCLUDED.embedding, -- Atualiza o vetor se o produto mudar
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
        Busca Híbrida (Texto + Vetor) com RRF (Reciprocal Rank Fusion).
        Vetor: 384 dim (Local)
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
                latest.price_amount, 
                latest.currency,
                (COALESCE(s.score_vec, 0.0) + COALESCE(k.score_text, 0.0)) AS final_score
            FROM products p
            LEFT JOIN semantic_search s ON p.product_id = s.product_id
            LEFT JOIN keyword_search k ON p.product_id = k.product_id
            LEFT JOIN LATERAL (
                SELECT price_amount, currency 
                FROM price_history ph 
                WHERE ph.product_id = p.product_id 
                ORDER BY scraped_at DESC 
                LIMIT 1
            ) latest ON true
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