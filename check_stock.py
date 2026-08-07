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
import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

import requests

SKU = "258130"
PRODUCT_URL = (
    "https://www.pricesmart.com/en-cr/product/"
    "breakstones-cottage-cheese-680-g-1-5-lb-258130/258130"
)
API_URL = "https://www.pricesmart.com/api/ct/getProduct"
STATE_FILE = Path(__file__).parent / "state.json"

# Códigos de tienda (channel "key") confirmados desde la respuesta real de
# la API. No hace falta capturarlos manualmente.
STORES = {
    "Escazú": "6402",
    "Santa Ana": "6407",
    "Zapote": "6401",
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
    resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=25)
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
        print("⚠️  Faltan variables de email, se omite el envío.")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
    print("📧 Email enviado.")


def send_telegram(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        print("⚠️  Faltan variables de Telegram, se omite el mensaje.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url, data={"chat_id": chat_id, "text": text}, timeout=20
    )
    if resp.status_code >= 300:
        print(f"⚠️  Error enviando Telegram: {resp.status_code} {resp.text}")
    else:
        print("📲 Telegram enviado.")


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
    try:
        data = fetch_product_data()
    except requests.RequestException as e:
        print(f"❌ Error consultando la API: {e}")
        return

    try:
        by_key = get_channel_availability(data)
    except ValueError as e:
        print(f"❓ {e}")
        print("JSON crudo (primeros 4000 caracteres):")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:4000])
        return

    state = load_state()
    newly_available = []

    for store, key in STORES.items():
        info = by_key.get(key)
        if info is None:
            print(f"⚠️  No se encontró la tienda {store} (key {key}) en la respuesta.")
            continue

        available = info["isOnStock"]
        qty = info["availableQuantity"]
        was_available = state.get(store, False)
        status = f"✅ disponible ({qty} unid.)" if available else "❌ agotado"
        print(f"{store}: {status}")

        if available and not was_available:
            newly_available.append(store)

        state[store] = available

    save_state(state)

    if newly_available:
        print(f"🔔 Notificando cambio a disponible en: {newly_available}")
        notify(newly_available)
    else:
        print("Sin cambios que notificar.")


if __name__ == "__main__":
    main()
