from typing import Optional
import re


def clean_price_str(price_str: str) -> Optional[float]:
    if not price_str: return None
    try:
        clean = re.sub(r'[^\d,.]', '', price_str)
        if ',' in clean:
            clean = clean.replace('.', '').replace(',', '.')
        return float(clean)
    except:
        return None
