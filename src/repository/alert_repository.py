from sqlalchemy import text
from typing import List, Dict, Any
from decimal import Decimal

from src.core.database import db_manager


class AlertRepository:
    
    async def create_alert(self, product_id: str, chat_id: int, target_price: float) -> int:
        sql = text("""
            INSERT INTO price_alerts (product_id, chat_id, target_price)
            VALUES (:pid, :cid, :target)
            RETURNING alert_id;
        """)
        
        async with await db_manager.get_session() as session:
            async with session.begin():
                result = await session.execute(sql, {
                    "pid": product_id,
                    "cid": chat_id,
                    "target": target_price
                })
                return result.scalar()

    async def get_active_alerts(self) -> List[Dict[str, Any]]:

        sql = text("""
            SELECT 
                pa.alert_id, 
                pa.chat_id, 
                pa.target_price, 
                pa.product_id,
                p.url, 
                p.title
            FROM price_alerts pa
            JOIN products p ON pa.product_id = p.product_id
            WHERE pa.is_active = TRUE
        """)
        
        async with await db_manager.get_session() as session:
            result = await session.execute(sql)
            return [dict(row) for row in result.mappings().all()]

    async def deactivate_alert(self, alert_id: int):
        sql = text("UPDATE price_alerts SET is_active = FALSE WHERE alert_id = :aid")
        async with await db_manager.get_session() as session:
            async with session.begin():
                await session.execute(sql, {"aid": alert_id})