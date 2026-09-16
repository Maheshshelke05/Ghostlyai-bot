# Deploying to Render

This project is already set up to run on Render using **external managed Postgres (Neon) and
Redis (Upstash)** rather than Render's own database add-ons — if you're using Neon + Upstash
(as this project's own `.env` is configured for), you don't need Render's Postgres or Key Value
services at all. `render.yaml` at the repo root defines two services:

- **`ghostlyai-api`** — web service, runs the FastAPI app (Telegram webhook, admin API, `/health`)
- **`ghostlyai-worker`** — background worker, runs the digest/reminders/broadcast scheduler

Razorpay is optional to fill in right away — the app boots fine without it, payments just won't
work until you add the keys later. Every other piece (bot, admin API, Gemini resume parsing,
digest delivery) works without Razorpay configured.

## 1. Push this repo to GitHub

If you haven't already:

```bash
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

## 2. Get your Cloudinary credentials (resume storage)

Render's filesystem is ephemeral — anything written to local disk disappears on every deploy
and restart, so resumes must live somewhere external. This project already supports Cloudinary
for that (falls back to local disk automatically when unconfigured, which is fine for local dev
but not for Render).

1. Sign up free at [cloudinary.com](https://cloudinary.com).
2. On the dashboard, copy the **"API Environment variable"** value — it looks like
   `cloudinary://<api_key>:<api_secret>@<cloud_name>`.
3. You'll paste this in as `CLOUDINARY_URL` in step 4.

## 3. Create the Blueprint on Render

1. render.com → **New** → **Blueprint** → connect your GitHub account → pick this repo.
2. Render reads `render.yaml` and shows both services with a form for every `sync: false`
   variable. Fill these in for **both** services (`ghostlyai-api` and `ghostlyai-worker`):

   | Variable | Where to get it |
   |---|---|
   | `DATABASE_URL` | Your Neon connection string. Keep the `postgresql+asyncpg://` scheme (Neon gives you plain `postgresql://` — change it) and keep `?sslmode=require`; drop `channel_binding` if present, the app strips it automatically either way |
   | `REDIS_URL` | Your Upstash **`rediss://...`** URL (TLS) — not the `redis-cli` command Upstash shows you, just the URL portion of it |
   | `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
   | `TELEGRAM_WEBHOOK_SECRET` | Any random 32+ character string, e.g. generate with `openssl rand -hex 24` — **api service only** |
   | `SUPPORT_USERNAME` | Your Telegram @username, without the @ |
   | `ADMIN_ALERT_CHAT_ID` | Your numeric Telegram id (message [@userinfobot](https://t.me/userinfobot) to get it) |
   | `GEMINI_API_KEY` | From [Google AI Studio](https://aistudio.google.com/) |
   | `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` | Leave blank for now if you're doing Razorpay last — the app runs fine without them |
   | `JWT_SECRET` | Any random 64+ character string, e.g. `openssl rand -hex 32` — **must be the same value on both services** |
   | `CLOUDINARY_URL` | From step 2 |

3. Click **Apply**. Render builds both Docker images and starts the services.

## 4. Watch the first deploy

Open the `ghostlyai-api` service's **Logs** tab. On first boot it will:
1. Run `alembic upgrade head` automatically (the API does this itself on every production
   startup — see `app/main.py`; safe to run repeatedly, it's a no-op once up to date).
2. Register the Telegram webhook at `https://ghostlyai-api.onrender.com/webhooks/telegram`
   (or whatever URL Render actually assigned — check the service's page if `ghostlyai-api`
   was taken and Render appended a suffix).

If the assigned URL differs from `https://ghostlyai-api.onrender.com`, update the `BASE_URL`
value in the **`ghostlyai-worker`** service's environment variables to match (the worker has no
public URL of its own, so it can't infer this automatically the way the api service does) — the
api service handles this automatically via Render's injected `RENDER_EXTERNAL_URL`.

## 5. Create your admin login

Render's dashboard → `ghostlyai-api` service → **Shell** tab (gives you a terminal inside the
running container):

```bash
python -m app.scripts.create_admin
```

Answer the prompts (name, email, password, role = `owner`). This is interactive on purpose so
your password is never typed into a script, a chat, or a file.

## 6. Point the admin app at it

In `admin-app/eas.json`, set the `preview`/`production` profile's `EXPO_PUBLIC_API_URL` to your
Render URL, then build per `docs/APP_RELEASE.md`.

## 7. Verify

```bash
curl https://ghostlyai-api.onrender.com/health
# {"db":"ok","redis":"ok"}
```

Send `/start` to your bot on Telegram — you should get the language selection message within a
couple of seconds.

## Costs and plan choices (read before you rely on this in production)

- `render.yaml` defaults both services to the **Starter** plan. Render's **Free** plan exists
  for web services but spins down after 15 minutes of inactivity — the *next* Telegram update
  then waits 30-60+ seconds for a cold start, which is a poor experience and can cause Telegram
  to retry the webhook. Background workers have no free tier at all, since they need to run
  continuously to fire the 09:00/18:00 IST digest and other scheduled jobs on time. If you want
  to test cheaply first, Free is fine for `ghostlyai-api` alone, but budget for Starter (or
  higher) on both once you have real students depending on it.
- Neon's free Postgres tier and Upstash's free Redis tier are both generous enough for this
  project's scale at launch; check their pricing pages before you have thousands of users.

## Updating after code changes

Render auto-deploys on every push to your connected branch (unless you turned that off). To
change environment variables afterward, use the service's **Environment** tab — editing
`render.yaml` again only affects *new* variables it doesn't already know about, it won't
overwrite values you've already set through the dashboard.

## Alternative: the VPS + Docker Compose path

If you'd rather run this on your own VPS instead of Render (full control, no cold starts, no
per-service pricing tiers), `docs/DEPLOY.md` covers that end to end — same codebase, different
host.
