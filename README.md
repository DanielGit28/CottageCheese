# Stock notifier: Breakstone's cottage cheese at PriceSmart CR

Checks once a day, at 8:00 am Costa Rica time, whether the product is
available at Escazú, Santa Ana, Zapote, Tres Ríos, Cartago, and Llorente, 
and notifies you by email (Gmail) and Telegram every time
it finds stock at any of those stores.

A single API call is enough: the response returns availability for all
~60 PriceSmart stores in the region at once, so the script simply
filters the stores you care about from that response.

## Running it locally (with logs)

The script already has logging built in: the console shows a summary,
and `logs/check_stock.log` keeps the full detail of every API call
(payload sent, status code, response headers, how long it took). It
also saves the complete raw response of every run to
`logs/response_<date>_<time>.json`, in case you want to inspect it
later.

1. Clone the repo and enter the folder:
   ```bash
   git clone https://github.com/DanielGit28/CottageCheese.git
   cd CottageCheese
   ```
2. Create a virtual environment and install the dependency:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set up the notification variables. There are two ways (optional — if
   you skip this, the script keeps running and just tells you in the
   console/log that it skipped sending):

   **Option A — `.env` file (recommended, no need to repeat it every time):**
   ```bash
   cp .env.example .env
   ```
   Open `.env` with any editor and replace the example values with your
   own. The script loads it automatically on startup. `.env` is already
   in `.gitignore`, so it never gets pushed to the repo by accident.

   **Option B — export them in the terminal (lost when you close it):**
   ```bash
   export GMAIL_USER="youremail@gmail.com"
   export GMAIL_APP_PASSWORD="xxxxxxxxxxxxxxxx"
   export EMAIL_TO="youremail@gmail.com"
   export TELEGRAM_BOT_TOKEN="123456789:AAExxxxx..."
   export TELEGRAM_CHAT_ID="970504617"
   ```
   On Windows (PowerShell) it's `$env:GMAIL_USER="..."` instead of `export`.
4. Run the script:
   ```bash
   python3 check_stock.py
   ```
5. Check the detailed log:
   ```bash
   cat logs/check_stock.log
   ```
   Or the raw JSON of the latest response:
   ```bash
   ls logs/
   cat logs/response_20260807_153000.json | python3 -m json.tool | less
   ```

If you're going to keep it running locally instead of on GitHub Actions,
you'd need to schedule it yourself (e.g. with `cron` on Mac/Linux, or
Task Scheduler on Windows) so it runs once a day — GitHub Actions
already does that automatically, so running it locally is mainly useful
for testing and debugging.

> **Note:** the `logs/` folder is in `.gitignore` on purpose — it's not
> pushed to the repo. When it runs on GitHub Actions, those files only
> live within that specific run (you can see them in the **Actions**
> tab → that run → the "Run stock check" output); they don't
> accumulate across runs. If you want to keep them across Actions runs,
> the folder could be uploaded as an "artifact" — let me know if you'd
> like that added.

## Deploying it on GitHub Actions (automatic, free, in the cloud)

## ⚠️ Before you start

PriceSmart's site has a `robots.txt` that **does not allow automated
access**. This isn't illegal, but it may go against their Terms of
Service, and if you query too often they might block the IP (in this
case, GitHub Actions' servers). That's why the workflow is set to run
once a day. Use it at your own discretion and don't overload it.

## 1. Create the repository

1. Create a new GitHub repo (can be private).
2. Upload these 2 files:
   - `check_stock.py` → in the repo root
   - `check-cottage-cheese.yml` → inside the `.github/workflows/` folder
   - (you don't need to upload `README.md` if you don't want to, it's just for you)

## 2. Set up the repo's "Secrets"

In GitHub: `Settings → Secrets and variables → Actions → New repository secret`.
Create these:

| Secret | Value |
|---|---|
| `GMAIL_USER` | your Gmail address |
| `GMAIL_APP_PASSWORD` | see step 3 |
| `EMAIL_TO` | email address where you want to receive the alert |
| `TELEGRAM_BOT_TOKEN` | see step 3.5 |
| `TELEGRAM_CHAT_ID` | see step 3.5 |

## 3. Create a Gmail "App Password"

1. Turn on 2-step verification on your Google account, if you haven't already.
2. Go to https://myaccount.google.com/apppasswords
3. Generate an app password (16 characters) and use it as
   `GMAIL_APP_PASSWORD` (not your regular password).

## 3.5. Create a Telegram bot (optional but recommended)

1. In Telegram, search for **@BotFather** and send it `/newbot`. Give it
   a name and a username (it has to end in "bot", e.g. `cottage_stock_bot`).
2. BotFather will give you a **token** like `123456789:AAExxxxx...` —
   that's your `TELEGRAM_BOT_TOKEN`.
3. Open a chat with your newly created bot and send it any message
   (e.g. "hi") so it "knows" you.
4. Open in your browser:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   (replace `<YOUR_TOKEN>` with the real token). You'll see a JSON with
   `"chat":{"id":123456789,...}` — that number is your `TELEGRAM_CHAT_ID`.

If you don't want to use Telegram, you can leave those 2 variables
empty: the script simply skips the message and only sends email.

## 4. Manual test

In GitHub → **Actions** tab → select the workflow → **Run workflow**
(manual button, thanks to `workflow_dispatch`). Check the log:

- If you see `✅ in stock` or `❌ out of stock` for each store, everything's working.
- If you see `❓ Unexpected response structure`, something changed in
  PriceSmart's API; paste me the raw JSON that shows up in the log and
  I'll adjust the script.

## About repeated notifications

The script no longer keeps state between runs: it notifies you **every
time** it finds stock at any store, regardless of whether it already
notified you on the previous run. Since the product tends to sell out
quickly (1–2 days), this is intentional — so you find out on each daily
run while it's still available, instead of only once when it first
appears.

If at some point you'd rather go back to the "only notify once per
change from out-of-stock to in-stock" behavior, let me know and I'll
bring back the `state.json` logic.

## Adjusting the frequency

In `check-cottage-cheese.yml`, the line `cron: "0 14 * * *"` controls
the frequency (cron format, always in **UTC**, not local time). Right
now it runs once a day at 14:00 UTC, which is 8:00 am in Costa Rica
(UTC-6, year-round, no daylight saving). For example, to run it at
6:00 am CR time it would be `0 12 * * *`, or twice a day (8am and 6pm
CR) it would be `cron: "0 0,14 * * *"`.
GitHub Actions' free tier has limited monthly minutes on private repos;
on public repos it's unlimited.