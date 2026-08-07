#!/usr/bin/env python3
"""
Chequea disponibilidad del queso cottage Breakstone's (SKU 258130) en
PriceSmart Costa Rica para Escazú, Santa Ana y Zapote, y notifica por
email cuando pasa de "no disponible" a "disponible".

Guarda el último estado conocido en state.json para no repetir avisos.
"""

import json
import os
import re
import smtplib
import sys
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

# channelId de cada tienda -> se obtienen inspeccionando la pestaña Network
# del navegador con cada tienda seleccionada en el sitio (ver README.md)
STORES = {
    "Escazú": os.environ.get("CHANNEL_ESCAZU", ""),
    "Santa Ana": os.environ.get("CHANNEL_SANTA_ANA", ""),
    "Zapote": os.environ.get("CHANNEL_ZAPOTE", ""),
}

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


def fetch_store_data(channel_id: str) -> dict:
    payload = [
        {"skus": [SKU]},
        {
            "products": "getProductBySKU",
            "metadata": {"channelId": channel_id},
        },
    ]
    resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return resp.json()


def find_stock_signals(node, path="root"):
    """
    Recorre el JSON de forma recursiva buscando cualquier campo típico
    de disponibilidad (isOnStock, inStock, availableQuantity, etc).
    Devuelve una lista de (path, dict_encontrado) para depuración y
    para decidir si hay stock.
    """
    found = []
    keys_of_interest = {
        "isOnStock",
        "inStock",
        "availableQuantity",
        "availableForOrder",
        "quantityOnStock",
    }
    if isinstance(node, dict):
        if keys_of_interest & node.keys():
            found.append((path, node))
        for k, v in node.items():
            found.extend(find_stock_signals(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found.extend(find_stock_signals(v, f"{path}[{i}]"))
    return found


def is_available(data) -> tuple:
    """
    Devuelve (disponible: bool|None, señales_crudas: list).
    None significa "no pude interpretarlo, revisa el JSON crudo".
    """
    signals = find_stock_signals(data)
    if not signals:
        return None, signals

    for _, sig in signals:
        if sig.get("isOnStock") is True:
            return True, signals
        if sig.get("inStock") is True:
            return True, signals
        qty = sig.get("availableQuantity") or sig.get("quantityOnStock")
        if isinstance(qty, (int, float)) and qty > 0:
            return True, signals
        if sig.get("availableForOrder") is True:
            return True, signals

    return False, signals


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


def notify(available_stores: list):
    subject = "🧀 ¡Queso cottage disponible en PriceSmart!"
    stores_txt = ", ".join(available_stores)
    body = (
        f"El queso cottage Breakstone's (SKU {SKU}) está disponible en: "
        f"{stores_txt}.\n\n{PRODUCT_URL}"
    )
    send_email(subject, body)


def main():
    missing = [name for name, cid in STORES.items() if not cid]
    if missing:
        print(
            "⚠️  No hay channelId configurado para: "
            + ", ".join(missing)
            + ". Revisa el README para obtenerlo."
        )

    state = load_state()
    newly_available = []
    results = {}

    for store, channel_id in STORES.items():
        if not channel_id:
            continue
        try:
            data = fetch_store_data(channel_id)
        except requests.RequestException as e:
            print(f"❌ Error consultando {store}: {e}")
            continue

        available, signals = is_available(data)
        results[store] = available

        if available is None:
            print(f"❓ {store}: no pude interpretar la respuesta. JSON crudo:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:4000])
            continue

        was_available = state.get(store, False)
        status = "✅ disponible" if available else "❌ agotado"
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
