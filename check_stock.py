#!/usr/bin/env python3
"""
Checks availability of Breakstone's cottage cheese (SKU 258130) at
PriceSmart Costa Rica across several stores, and notifies by email
(Gmail) and Telegram every time it finds stock available at any of them.

A single API call returns availability for ALL stores (60 locations
across several countries), so we just filter the ones we care about by
their store code ("key").
"""

import json
import logging
import os
import smtplib
import time
from email.mime.text import MIMEText
from pathlib import Path

import requests

# Load variables from a .env file if present (local use only; on GitHub
# Actions the variables are already injected as secrets).
_DOTENV_STATUS = None
try:
    from dotenv import find_dotenv, load_dotenv

    _dotenv_path = find_dotenv(usecwd=True)
    if _dotenv_path:
        load_dotenv(_dotenv_path, override=True)
        _DOTENV_STATUS = f"Loaded .env from: {_dotenv_path}"
    else:
        _DOTENV_STATUS = (
            "No .env file found in the current directory "
            f"({os.getcwd()}) or any parent directory."
        )
except ImportError:
    _DOTENV_STATUS = (
        "python-dotenv is not installed — .env is NOT being loaded. "
        "Install it with: pip install python-dotenv"
    )

SKU = "258130"
PRODUCT_URL = (
    "https://www.pricesmart.com/en-cr/product/"
    "breakstones-cottage-cheese-680-g-1-5-lb-258130/258130"
)
API_URL = "https://www.pricesmart.com/api/ct/getProduct"
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Logger for console output (INFO level) and for the log file (DEBUG
# level, includes the full detail of every API call).
logger = logging.getLogger("check_stock")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

file_handler = logging.FileHandler(
    LOG_DIR / "check_stock.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
)
logger.addHandler(file_handler)

logger.info(_DOTENV_STATUS)

# Store codes (channel "key") confirmed from a real API response.
# No need to capture them manually via DevTools.
STORES = {
    "Escazú": "6402",
    "Santa Ana": "6407",
    "Zapote": "6401",
    "Tres Ríos": "6406",
    "Cartago": "6409",
    "Llorente": "6404",
}

# Any valid channelId works as request "metadata"; the API returns
# availability for all ~60 stores regardless. We use Escazú's.
ANY_CHANNEL_ID = "bafd6a6d-a619-4a39-bf47-fa4e1bf09770"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://www.pricesmart.com",
    "Referer": PRODUCT_URL,
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}


def fetch_product_data() -> dict:
    payload = [
        {"skus": [SKU]},
        {
            "products": "getProductBySKU",
            "metadata": {"channelId": ANY_CHANNEL_ID},
        },
    ]

    logger.debug("→ POST %s", API_URL)
    logger.debug("→ Headers: %s", json.dumps(HEADERS, indent=2))
    logger.debug("→ Payload: %s", json.dumps(payload, indent=2))

    start = time.monotonic()
    resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=25)
    elapsed = time.monotonic() - start

    logger.debug(
        "← Status: %s | Time: %.2fs | Response headers: %s",
        resp.status_code,
        elapsed,
        dict(resp.headers),
    )

    # Save the full raw response to a separate file for later inspection
    # (one per run, timestamped).
    dump_path = LOG_DIR / f"response_{time.strftime('%Y%m%d_%H%M%S')}.json"
    dump_path.write_text(resp.text, encoding="utf-8")
    logger.debug("← Response saved to: %s", dump_path)

    resp.raise_for_status()
    return resp.json()


def get_channel_availability(data: dict) -> dict:
    """
    Returns {channel_key: {"isOnStock": bool, "availableQuantity": int}}
    from the full API response.
    """
    try:
        results = data["data"]["products"]["results"]
        variant = results[0]["masterData"]["current"]["masterVariant"]
        channels = variant["availability"]["channels"]["results"]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Unexpected response structure: {e}")

    by_key = {}
    for entry in channels:
        key = entry["channel"]["key"]
        avail = entry["availability"]
        by_key[key] = {
            "isOnStock": avail.get("isOnStock", False),
            "availableQuantity": avail.get("availableQuantity", 0),
        }
    return by_key


def send_email(subject: str, body: str):
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    to_addr = os.environ.get("EMAIL_TO")
    if not (user and password and to_addr):
        logger.warning("Missing email variables, skipping email.")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
    logger.info("📧 Email sent.")


def send_telegram(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        logger.warning("Missing Telegram variables, skipping message.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url, data={"chat_id": chat_id, "text": text}, timeout=20
    )
    if resp.status_code >= 300:
        logger.error("Error sending Telegram message: %s %s",
                     resp.status_code, resp.text)
    else:
        logger.info("📲 Telegram message sent.")


def notify(available_stores: list):
    subject = "🧀 Cottage cheese is available at PriceSmart!"
    stores_txt = ", ".join(available_stores)
    body = (
        f"Breakstone's cottage cheese (SKU {SKU}) is available at: "
        f"{stores_txt}.\n\n{PRODUCT_URL}"
    )
    send_email(subject, body)
    send_telegram(body)


def main():
    logger.info("=" * 60)
    logger.info("Starting stock check — %s",
                time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        data = fetch_product_data()
    except requests.RequestException as e:
        logger.error("Error calling the API: %s", e)
        return

    try:
        by_key = get_channel_availability(data)
    except ValueError as e:
        logger.error(str(e))
        logger.debug("Raw JSON (first 4000 characters):")
        logger.debug(json.dumps(data, indent=2, ensure_ascii=False)[:4000])
        return

    stores_with_stock = []

    for store, key in STORES.items():
        info = by_key.get(key)
        if info is None:
            logger.warning(
                "Store %s (key %s) not found in the response.", store, key)
            continue

        available = info["isOnStock"]
        qty = info["availableQuantity"]
        status = f"✅ in stock ({qty} units)" if available else "❌ out of stock"
        logger.info("%s: %s", store, status)

        if available:
            stores_with_stock.append(store)

    if stores_with_stock:
        logger.info("🔔 Notifying about availability at: %s", stores_with_stock)
        notify(stores_with_stock)
    else:
        logger.info("Nothing in stock this run, no notification sent.")


if __name__ == "__main__":
    main()
