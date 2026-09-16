# Student Job Alert Bot

A Telegram bot that sends Maharashtra students daily job alerts matched to their education,
category and district, plus an Android admin app for uploading jobs and managing subscribers.
₹99/30 days via Razorpay, 3-day free trial, resumes parsed with Gemini. Full spec in
`Student_Job_Alert_Bot_Master_Plan.pdf`; engineering context lives in `CLAUDE.md`.

## Repository layout

```
backend/        FastAPI + aiogram bot + worker (Python 3.12)
admin-app/       Admin Android app (Expo + TypeScript)
deploy/          Docker Compose, nginx, backup script for the VPS
docs/            Deployment and app-release runbooks
.github/         CI (backend test suite)
```

## Backend — local development

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp ../.env.example ../.env      # fill in BOT_TOKEN, GEMINI_API_KEY etc. as you get them
```

Run the test suite (no Postgres/Redis needed — tests use in-memory SQLite):

```bash
pytest -q
```

Run a local Postgres + Redis + API via Docker:

```bash
docker compose -f ../deploy/docker-compose.dev.yml up
docker compose -f ../deploy/docker-compose.dev.yml exec api alembic upgrade head
docker compose -f ../deploy/docker-compose.dev.yml exec api python -m app.db.seed
```

Run the bot with long polling against that API (needs a real `BOT_TOKEN` in `.env`):

```bash
python -m app.bot.polling
```

Run the background worker (digest, reminders, expiry, broadcasts):

```bash
python -m app.workers.scheduler
```

Interactive API docs once the API is running: `http://localhost:8000/docs`.

## Admin app — local development

```bash
cd admin-app
npm install
npx expo start
```

Set `EXPO_PUBLIC_API_URL` (e.g. in a `.env` file read by Expo, or inline before `expo start`) to
point at your running backend. Open in Expo Go on a phone, or `npx expo start --android` /
`--ios` with an emulator.

Type-check anytime with `npx tsc --noEmit`.

## Deploying to production

See `docs/DEPLOY.md` for the full VPS runbook (Docker Compose, SSL, webhooks, backups,
monitoring) and `docs/APP_RELEASE.md` for building the admin APK with EAS.

## Where things are documented

- **Business rules, pricing, roadmap**: `Student_Job_Alert_Bot_Master_Plan.pdf`
- **Engineering conventions, data model, locked tech decisions**: `CLAUDE.md`
- **API**: `http://localhost:8000/docs` (Swagger) once the backend is running
- **Deployment runbook**: `docs/DEPLOY.md`
- **Admin app release runbook**: `docs/APP_RELEASE.md`

## Status

Backend (bot, admin API, workers, payments, AI resume parsing) and the admin app (all screens
from the spec) are built and wired end to end. Before going live you still need to supply real
secrets (Telegram bot token, Gemini API key, Razorpay keys, a domain + VPS) — see the checklists
in `docs/DEPLOY.md` and Chapter 30 of the master plan PDF.
