#!/usr/bin/env python3
"""
Chequea disponibilidad del queso cottage Breakstone's (SKU 258130) en
PriceSmart Costa Rica para Escazú, Santa Ana y Zapote, y notifica por
email (Gmail) solo cuando pasa de "no disponible" a "disponible".

Una sola llamada a la API trae la disponibilidad de TODAS las tiendas
(60 sucursales en varios países), así que solo filtramos las que nos
interesan por su código de tienda ("key").

Guarda el último estado conocido en state.json para no repetir avisos.
"""

import json
import logging
import os
import smtplib
import time
from email.mime.text import MIMEText
from pathlib import Path

import requests

# Carga variables desde un archivo .env si existe (solo afecta uso local;
# en GitHub Actions las variables ya vienen inyectadas como secrets).
_DOTENV_STATUS = None
try:
    from dotenv import find_dotenv, load_dotenv

    _dotenv_path = find_dotenv(usecwd=True)
    if _dotenv_path:
        load_dotenv(_dotenv_path, override=True)
        _DOTENV_STATUS = f"Cargado .env desde: {_dotenv_path}"
    else:
        _DOTENV_STATUS = (
            "No se encontró un archivo .env en el directorio actual "
            f"({os.getcwd()}) ni en sus carpetas padre."
        )
except ImportError:
    _DOTENV_STATUS = (
        "python-dotenv no está instalado — el .env NO se está cargando. "
        "Instálalo con: pip install python-dotenv"
    )

SKU = "258130"
PRODUCT_URL = (
    "https://www.pricesmart.com/en-cr/product/"
    "breakstones-cottage-cheese-680-g-1-5-lb-258130/258130"
)
API_URL = "https://www.pricesmart.com/api/ct/getProduct"
STATE_FILE = Path(__file__).parent / "state.json"
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Logger para consola (nivel INFO) y para el archivo de log (nivel DEBUG,
# incluye el detalle de cada llamada a la API).
logger = logging.getLogger("check_stock")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

file_handler = logging.FileHandler(LOG_DIR / "check_stock.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
)
logger.addHandler(file_handler)

logger.info(_DOTENV_STATUS)

# Códigos de tienda (channel "key") confirmados desde la respuesta real de
# la API. No hace falta capturarlos manualmente.
STORES = {
    "Escazú": "6402",
    "Santa Ana": "6407",
    "Zapote": "6401",
    "Tres Ríos": "6406",
    "Cartago": "6409"
}

# Cualquier channelId válido sirve como "metadata" del request; la API
# igual devuelve la disponibilidad de las ~60 tiendas. Usamos el de Escazú.
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
        "← Status: %s | Tiempo: %.2fs | Response headers: %s",
        resp.status_code,
        elapsed,
        dict(resp.headers),
    )

    # Guarda la respuesta cruda completa en un archivo aparte, por si hay
    # que inspeccionarla con calma (uno por corrida, con timestamp).
    dump_path = LOG_DIR / f"response_{time.strftime('%Y%m%d_%H%M%S')}.json"
    dump_path.write_text(resp.text, encoding="utf-8")
    logger.debug("← Respuesta guardada en: %s", dump_path)

    resp.raise_for_status()
    return resp.json()


def get_channel_availability(data: dict) -> dict:
    """
    Devuelve {channel_key: {"isOnStock": bool, "availableQuantity": int}}
    a partir de la respuesta completa de la API.
    """
    try:
        results = data["data"]["products"]["results"]
        variant = results[0]["masterData"]["current"]["masterVariant"]
        channels = variant["availability"]["channels"]["results"]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Estructura de respuesta inesperada: {e}")

    by_key = {}
    for entry in channels:
        key = entry["channel"]["key"]
        avail = entry["availability"]
        by_key[key] = {
            "isOnStock": avail.get("isOnStock", False),
            "availableQuantity": avail.get("availableQuantity", 0),
        }
    return by_key


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def send_email(subject: str, body: str):
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    to_addr = os.environ.get("EMAIL_TO")
    if not (user and password and to_addr):
        logger.warning("Faltan variables de email, se omite el envío.")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
    logger.info("📧 Email enviado.")


def send_telegram(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        logger.warning("Faltan variables de Telegram, se omite el mensaje.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url, data={"chat_id": chat_id, "text": text}, timeout=20
    )
    if resp.status_code >= 300:
        logger.error("Error enviando Telegram: %s %s", resp.status_code, resp.text)
    else:
        logger.info("📲 Telegram enviado.")


def notify(available_stores: list):
    subject = "🧀 ¡Queso cottage disponible en PriceSmart!"
    stores_txt = ", ".join(available_stores)
    body = (
        f"El queso cottage Breakstone's (SKU {SKU}) está disponible en: "
        f"{stores_txt}.\n\n{PRODUCT_URL}"
    )
    send_email(subject, body)
    send_telegram(body)


def main():
    logger.info("=" * 60)
    logger.info("Iniciando chequeo de stock — %s", time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        data = fetch_product_data()
    except requests.RequestException as e:
        logger.error("Error consultando la API: %s", e)
        return

    try:
        by_key = get_channel_availability(data)
    except ValueError as e:
        logger.error(str(e))
        logger.debug("JSON crudo (primeros 4000 caracteres):")
        logger.debug(json.dumps(data, indent=2, ensure_ascii=False)[:4000])
        return

    state = load_state()
    newly_available = []

    for store, key in STORES.items():
        info = by_key.get(key)
        if info is None:
            logger.warning("No se encontró la tienda %s (key %s) en la respuesta.", store, key)
            continue

        available = info["isOnStock"]
        qty = info["availableQuantity"]
        was_available = state.get(store, False)
        status = f"✅ disponible ({qty} unid.)" if available else "❌ agotado"
        logger.info("%s: %s", store, status)

        if available and not was_available:
            newly_available.append(store)

        state[store] = available

    save_state(state)

    if newly_available:
        logger.info("🔔 Notificando cambio a disponible en: %s", newly_available)
        notify(newly_available)
    else:
        logger.info("Sin cambios que notificar.")


if __name__ == "__main__":
    main()