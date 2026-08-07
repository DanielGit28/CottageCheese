# Notificador de stock: queso cottage Breakstone's en PriceSmart CR

Revisa cada 2 horas si el producto está disponible en Escazú, Santa Ana o
Zapote, y te avisa por email (Gmail) solo cuando pasa de "agotado" a
"disponible" (no en cada corrida).

Con una sola llamada a la API basta: la respuesta trae la disponibilidad
de las ~60 tiendas de PriceSmart en la región de una vez, así que el
script simplemente filtra Escazú (`6402`), Santa Ana (`6407`) y Zapote
(`6401`) de esa respuesta.

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

## 3. Crea un "App Password" de Gmail

1. Activa verificación en 2 pasos en tu cuenta de Google, si no la tienes.
2. Ve a https://myaccount.google.com/apppasswords
3. Genera una contraseña de aplicación (16 caracteres) y úsala como
   `GMAIL_APP_PASSWORD` (no tu contraseña normal).

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
