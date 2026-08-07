# Notificador de stock: queso cottage Breakstone's en PriceSmart CR

Revisa cada 2 horas si el producto está disponible en Escazú, Santa Ana
o Zapote, y te avisa por email (Gmail) solo cuando pasa de "agotado" a
"disponible" (no en cada corrida).

## ⚠️ Antes de empezar

El sitio de PriceSmart tiene un `robots.txt` que **no permite acceso
automatizado**. Esto no es algo técnico ilegal, pero sí puede ir contra sus
Términos de Servicio, y si consultan muy seguido te pueden bloquear la IP
(en este caso, la de los servidores de GitHub Actions). Por eso el
workflow está configurado a cada 2 horas. Úsalo bajo tu propio criterio y
no lo satures.

## 1. Crea el repositorio

1. Crea un repo nuevo en GitHub (puede ser privado).
2. Sube estos 3 archivos:
   - `check_stock.py` → en la raíz del repo
   - `check-cottage-cheese.yml` → dentro de la carpeta `.github/workflows/`
   - (no subas `README.md` si no quieres, es solo para vos)

## 2. Consigue el `channelId` de cada tienda

El `channelId` que capturaste (`bafd6a6d-a619-4a39-bf47-fa4e1bf09770`)
corresponde a la tienda que tenías seleccionada en el navegador en ese
momento — probablemente no sirve para las 3 sucursales. Necesitas uno por
tienda:

1. Abre la página del producto en Chrome/Edge.
2. Abre DevTools (F12) → pestaña **Network** → filtra por `getProduct`.
3. En el sitio, cambia la tienda seleccionada a **Escazú** (normalmente
   hay un selector de tienda/sucursal en la parte superior del sitio).
4. Recarga la página del producto y busca la llamada a
   `api/ct/getProduct` en Network → pestaña **Payload/Request** → copia el
   valor de `metadata.channelId`.
5. Repite cambiando la tienda a **Santa Ana** y luego a **Zapote**.

Vas a terminar con 3 UUIDs distintos.

## 3. Configura los "Secrets" del repo

En GitHub: `Settings → Secrets and variables → Actions → New repository secret`.
Crea estos:

| Secret | Valor |
|---|---|
| `CHANNEL_ESCAZU` | UUID de Escazú |
| `CHANNEL_SANTA_ANA` | UUID de Santa Ana |
| `CHANNEL_ZAPOTE` | UUID de Zapote |
| `GMAIL_USER` | tu correo de Gmail |
| `GMAIL_APP_PASSWORD` | ver paso 4 |
| `EMAIL_TO` | correo donde quieres recibir el aviso |

## 4. Crea un "App Password" de Gmail (para el email)

1. Activa verificación en 2 pasos en tu cuenta de Google, si no la tienes.
2. Ve a https://myaccount.google.com/apppasswords
3. Genera una contraseña de aplicación (16 caracteres) y úsala como
   `GMAIL_APP_PASSWORD` (no tu contraseña normal).

## 5. Prueba manual

En GitHub → pestaña **Actions** → selecciona el workflow → **Run
workflow** (botón manual, gracias a `workflow_dispatch`). Revisa el log:

- Si ves `❓ no pude interpretar la respuesta` con un JSON crudo debajo,
  pégamelo en el chat y ajusto la función `is_available()` del script
  para que lea el campo correcto de disponibilidad.
- Si todo va bien, verás `✅ disponible` o `❌ agotado` por cada tienda.

## Cómo funciona el "no repetir avisos"

El script guarda el último estado conocido en `state.json` dentro del
mismo repo (el workflow lo hace commit automáticamente). Solo te notifica
cuando una tienda pasa de `false` a `true`, así no te bombardea cada 20
minutos mientras siga disponible.

## Ajustar la frecuencia

En `check-cottage-cheese.yml`, la línea `cron: "0 */2 * * *"` controla
la frecuencia (formato cron, en UTC): corre al minuto 0 de cada 2 horas.
Por ejemplo, cada hora sería `0 * * * *`, o cada 30 min `*/30 * * * *`.
GitHub Actions free tier en repos privados tiene minutos limitados al
mes, en repos públicos es ilimitado — otra razón para no bajar demasiado
el intervalo.
