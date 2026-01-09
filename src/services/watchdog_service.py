import httpx


from src.repository.alert_repository import AlertRepository
from src.services.scrapper_service import ScraperEngine
from src.services.catalog_service import CatalogService
from src.telegram.message import send_message
from src.core.logger import logger

class WatchdogService:
    def __init__(self):
        self.alert_repo = AlertRepository()
        self.catalog_service = CatalogService() 
        self.scraper = ScraperEngine()

    async def run_cycle(self):

        logger.info("🐕 Watchdog Cycle Started...")
        alerts = await self.alert_repo.get_active_alerts()
        
        if not alerts:
            logger.info("No active alerts to check.")
            return

        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for alert in alerts:
                try:
                    await self._check_single_alert(client, alert)
                except Exception as e:
                    logger.error(f"Error checking alert {alert['alert_id']}: {e}")
        
        logger.info("🐕 Watchdog Cycle Finished.")

    async def _check_single_alert(self, client: httpx.AsyncClient, alert: dict):
        url = alert['url']
        target = float(alert['target_price'])
        
        headers = {
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        resp = await client.get(url, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            return

        result = self.scraper.extract_price(resp.text, url)
        
        if not result.has_price:
            return

        current_price = result.current_price

        await self.catalog_service.register_product(
            url=url, 
            title=alert['title'], 
            price=current_price,
            description="Watchdog Update"
        )

        if current_price <= target:
            logger.info(f"🚨 TARGET HIT! Alert {alert['alert_id']}: {current_price} <= {target}")
            
            msg = (
                f"🚨 <b>ALERTA DE PREÇO ATINGIDO!</b>\n\n"
                f"📦 {alert['title']}\n"
                f"🎯 Alvo: R$ {target:.2f}\n"
                f"🔥 <b>Atual: R$ {current_price:.2f}</b>\n\n"
                f"🔗 <a href='{url}'>COMPRAR AGORA</a>"
            )
            await send_message(alert['chat_id'], msg)
            
            await self.alert_repo.deactivate_alert(alert['alert_id'])