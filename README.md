# Notificador de stock: queso cottage Breakstone's en PriceSmart CR

Revisa cada 2 horas si el producto está disponible en Escazú, Santa Ana,
Zapote, Tres Ríos y Cartago, y te avisa por email (Gmail) y
Telegram solo cuando pasa de "agotado" a "disponible" (no en cada corrida).

Con una sola llamada a la API basta: la respuesta trae la disponibilidad
de las ~60 tiendas de PriceSmart en la región de una vez, así que el
script simplemente filtra las tiendas que te interesan de esa respuesta.

## Correrlo localmente (con logs)

El script ya trae logging integrado: en consola muestra un resumen, y
en `logs/check_stock.log` queda el detalle completo de cada llamada a la
API (payload enviado, status code, headers de respuesta, tiempo que
tardó). Además guarda la respuesta cruda completa de cada corrida en
`logs/response_<fecha>_<hora>.json`, por si quieres revisarla con calma.

1. Clona el repo y entra a la carpeta:
   ```bash
   git clone https://github.com/DanielGit28/CottageCheese.git
   cd CottageCheese
   ```
2. Crea un entorno virtual e instala la dependencia:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # en Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Exporta las variables de notificación (opcional — si las omites, el
   script sigue corriendo y solo te avisa en consola/log que se saltó el
   envío):
   ```bash
   export GMAIL_USER="tucorreo@gmail.com"
   export GMAIL_APP_PASSWORD="xxxxxxxxxxxxxxxx"
   export EMAIL_TO="tucorreo@gmail.com"
   export TELEGRAM_BOT_TOKEN="123456789:AAExxxxx..."
   export TELEGRAM_CHAT_ID="970504617"
   ```
   En Windows (PowerShell) es `$env:GMAIL_USER="..."` en vez de `export`.
4. Corre el script:
   ```bash
   python3 check_stock.py
   ```
5. Revisa el log detallado:
   ```bash
   cat logs/check_stock.log
   ```
   O el JSON crudo de la última respuesta:
   ```bash
   ls logs/
   cat logs/response_20260807_153000.json | python3 -m json.tool | less
   ```

Si vas a dejarlo corriendo local en vez de en GitHub Actions, tendrías
que programarlo tú mismo (ej. con `cron` en Mac/Linux, o el Programador
de tareas en Windows) para que se ejecute cada 2 horas — GitHub Actions
ya hace eso automáticamente, así que lo local es principalmente útil
para probar y depurar.

> **Nota:** la carpeta `logs/` está en `.gitignore` a propósito — no se
> sube al repo. Cuando corre en GitHub Actions, esos archivos solo viven
> dentro de esa ejecución puntual (los ves en la pestaña **Actions** →
> esa corrida → el output de "Run stock check"); no se acumulan entre
> corridas. Si quieres conservarlos entre corridas de Actions, se puede
> subir la carpeta como "artifact" — avísame si quieres que lo agregue.

## Desplegarlo en GitHub Actions (automático, gratis, en la nube)

## ⚠️ Antes de empezar

El sitio de PriceSmart tiene un `robots.txt` que **no permite acceso
automatizado**. Esto no es algo técnico ilegal, pero sí puede ir contra sus
Términos de Servicio, y si consultan muy seguido te pueden bloquear la IP
(en este caso, la de los servidores de GitHub Actions). Por eso el
workflow está configurado a cada 2 horas. Úsalo bajo tu propio criterio y
no lo satures.

## 1. Crea el repositorio

1. Crea un repo nuevo en GitHub (puede ser privado).
2. Sube estos 2 archivos:
   - `check_stock.py` → en la raíz del repo
   - `check-cottage-cheese.yml` → dentro de la carpeta `.github/workflows/`
   - (no subas `README.md` si no quieres, es solo para vos)

## 2. Configura los "Secrets" del repo

En GitHub: `Settings → Secrets and variables → Actions → New repository secret`.
Crea estos:

| Secret | Valor |
|---|---|
| `GMAIL_USER` | tu correo de Gmail |
| `GMAIL_APP_PASSWORD` | ver paso 3 |
| `EMAIL_TO` | correo donde quieres recibir el aviso |
| `TELEGRAM_BOT_TOKEN` | ver paso 3.5 |
| `TELEGRAM_CHAT_ID` | ver paso 3.5 |

## 3. Crea un "App Password" de Gmail

1. Activa verificación en 2 pasos en tu cuenta de Google, si no la tienes.
2. Ve a https://myaccount.google.com/apppasswords
3. Genera una contraseña de aplicación (16 caracteres) y úsala como
   `GMAIL_APP_PASSWORD` (no tu contraseña normal).

## 3.5. Crea un bot de Telegram (opcional pero recomendado)

1. En Telegram, busca **@BotFather** y mándale `/newbot`. Ponle un nombre
   y un username (tiene que terminar en "bot", ej. `cottage_stock_bot`).
2. BotFather te va a dar un **token** como `123456789:AAExxxxx...` — ese
   es tu `TELEGRAM_BOT_TOKEN`.
3. Abre un chat con tu bot recién creado y mándale cualquier mensaje
   (ej. "hola") para que te "conozca".
4. Abre en el navegador:
   `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
   (reemplaza `<TU_TOKEN>` por el token real). Ahí vas a ver un JSON con
   `"chat":{"id":123456789,...}` — ese número es tu `TELEGRAM_CHAT_ID`.

Si no quieres usar Telegram, puedes dejar esas 2 variables vacías: el
script simplemente se salta el mensaje y solo manda email.

## 4. Prueba manual

En GitHub → pestaña **Actions** → selecciona el workflow → **Run
workflow** (botón manual, gracias a `workflow_dispatch`). Revisa el log:

- Si ves `✅ disponible` o `❌ agotado` por cada tienda, todo funciona.
- Si ves `❓ Estructura de respuesta inesperada`, algo cambió en la API de
  PriceSmart; pégame el JSON crudo que aparece en el log y ajusto el
  script.

## Cómo funciona el "no repetir avisos"

El script guarda el último estado conocido en `state.json` dentro del
mismo repo (el workflow lo hace commit automáticamente). Solo te notifica
cuando una tienda pasa de `false` a `true`, así no te bombardea cada 2
horas mientras siga disponible.

## Ajustar la frecuencia

En `check-cottage-cheese.yml`, la línea `cron: "0 */2 * * *"` controla
la frecuencia (formato cron, en UTC): corre al minuto 0 de cada 2 horas.
Por ejemplo, cada hora sería `0 * * * *`, o cada 30 min `*/30 * * * *`.
GitHub Actions free tier en repos privados tiene minutos limitados al
mes, en repos públicos es ilimitado — otra razón para no bajar demasiado
el intervalo.