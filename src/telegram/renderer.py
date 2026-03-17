import json
import html  


def format_telegram_message(llm_response: str) -> str:
    """
    Renders the Agent's JSON response into a formatted HTML message for Telegram.
    Supports bilingual UI labels based on the 'lang' field (pt/en).
    """
    try:
        clean_response = llm_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_response)
        
        if not isinstance(data, dict):
            return html.escape(llm_response)
        
        lang = data.get("lang", "en").lower()
        
        labels = {
            "en": {
                "view_offer": "View Offer",
                "price": "Price",
                "source": "Source",
                "on_request": "On Request",
                "out_of_stock": "Out of Stock"
            },
            "pt": {
                "view_offer": "Ver Oferta",
                "price": "Preço",
                "source": "Fonte",
                "on_request": "Sob Consulta",
                "out_of_stock": "Esgotado"
            }
        }
        
        t = labels.get(lang, labels["en"])
        
        message = ""
        
        if "voice" in data and data["voice"]:
            message += f"{html.escape(data['voice'])}\n\n"
            
        items = data.get("items", [])
        if items:
            for item in items:
                title = html.escape(item.get('title', 'Product'))
                url = item.get('url', '#')
                
                price = item.get("price")
                original_price = item.get("original_price")
                
                if not price or str(price).lower() == "none":
                    price = t["on_request"]
                
                price_str = str(price).lower()
                source_str = str(item.get("source", "")).lower()

                if "options" in price_str or "list" in source_str:
                    icon = "📋" 
                elif any(x in price_str for x in ["view", "site", "consulta", "request"]):
                    icon = "🔎" 
                else:
                    icon = "📦"

                message += f"{icon} <b>{title}</b>\n"
                message += f"🔗 <a href=\"{url}\">{t['view_offer']}</a>\n"
                
                if original_price and original_price != "null" and original_price != price:
                     message += f"💰 <b>{t['price']}:</b> <s>{original_price}</s> ➔ <b>{price}</b> 🔥\n"
                else:
                     message += f"💰 <b>{t['price']}:</b> {price}\n"
                
                source = html.escape(item.get("source", "Store"))
                message += f"🏪 <b>{t['source']}:</b> {source}\n"
                
                message += "\n"
            
        if "footer" in data and data["footer"]:
            message += f"<i>{html.escape(data['footer'])}</i>"
            
        return message if message.strip() else "..."
        
    except json.JSONDecodeError:
        return html.escape(llm_response)
    except Exception as e:
        return f"Rendering error: {html.escape(str(e))}"