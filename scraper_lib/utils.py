import time, random, re
from datetime import datetime, timezone
from typing import Optional, Tuple

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
]

def jitter_sleep(base: float = 1.0, spread: float = 0.5):
    time.sleep(max(0.1, base + random.uniform(-spread, spread)))

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def normalize_price(raw: str):
    if not raw:
        return None, None
    s = raw.strip().replace("\xa0", " ").replace("\u202f"," ").replace(",", ".")
    import re
    m = re.search(r"([€$£]|EUR|USD|GBP)", s, flags=re.I)
    currency = m.group(1).upper() if m else None
    nums = re.findall(r"[0-9]+\.?[0-9]*", s)
    if not nums:
        return None, currency
    try:
        val = float(nums[0])
        return val, currency or "EUR"
    except Exception:
        return None, currency

def clean_text(s):
    if s is None: return None
    import re
    return re.sub(r"\s+", " ", s).strip()