import json
import html  


def format_telegram_message(llm_response: str) -> str:
    try:
        clean_response = llm_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_response)
        
        if not isinstance(data, dict):
            return html.escape(llm_response)
        
        message = ""
        
        if "voice" in data and data["voice"]:
            message += f"{html.escape(data['voice'])}\n\n"
            
        items = data.get("items", [])
        if items:
            for item in items:
                title = html.escape(item.get('title', 'Produto'))
                url = item.get('url', '#')
                
                price = item.get("price")
                original_price = item.get("original_price")
                
                if not price or str(price).lower() == "none":
                    price = "Sob Consulta"
                elif "R$" not in str(price) and str(price).replace(".", '', 1).isdigit():
                    price = f"R$ {price}"

                price_str = str(price).lower()
                source_str = str(item.get("source", "")).lower()

                if "opções" in price_str or "lista" in source_str:
                    icon = "📋" 
                elif "ver no site" in price_str or "sob consulta" in price_str:
                    icon = "🔎" 
                else:
                    icon = "📦"

                message += f"{icon} <b>{title}</b>\n"
                message += f"🔗 <a href=\"{url}\">Ver Oferta</a>\n"
                
                if original_price and original_price != "null" and original_price != price:
                     if "R$" not in str(original_price): 
                         original_price = f"R$ {original_price}"
                     message += f"💰 <b>Preço:</b> <s>{original_price}</s> ➔ <b>{price}</b> 🔥\n"
                else:
                    message += f"💰 <b>Preço:</b> {price}\n"
                
                source = html.escape(item.get("source", "Loja"))
                message += f"🏪 <b>Fonte:</b> {source}\n"
                
                message += "\n"
            
        if "footer" in data and data["footer"]:
            message += f"<i>{html.escape(data['footer'])}</i>"
            
        return message if message.strip() else "..."
        
    except json.JSONDecodeError:
        return html.escape(llm_response)
    except Exception as e:
        return f"Rendering error: {html.escape(str(e))}"