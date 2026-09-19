# Student Job Alert Bot

A Telegram bot (and standalone student app) that sends Maharashtra students job alerts matched
to their education, category and district, plus an Android admin app for uploading jobs and
managing subscribers. ₹99/30 days via Razorpay, 3-day free trial, resumes parsed with Gemini.
Full spec in `Student_Job_Alert_Bot_Master_Plan.pdf`; engineering context lives in `CLAUDE.md`.

## Repository layout

```
backend/              FastAPI + aiogram bot + worker (Python 3.12)
admin-app/            Admin Android app (Expo + TypeScript)
ghotlyai-job-portal/  Student Android app (Expo + TypeScript) - resume-first signup, no bot needed
deploy/               Docker Compose, nginx, backup script for the production VPS
docs/                 Deployment and app-release runbooks
.github/              CI (backend tests) + APK build pipelines for both apps
```

Resume storage uses Cloudinary when `CLOUDINARY_URL` is set, falling back to local disk
otherwise (fine for local dev, or a VPS with a persistent volume). Production runs entirely on
a single self-hosted VPS via Docker Compose - Postgres and Redis are containers in that same
compose stack, not external managed services.

## Backend — local development

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt   # requirements.txt + pytest/aiosqlite for testing
cp ../.env.example ../.env      # fill in BOT_TOKEN, GEMINI_API_KEY etc. as you get them
```

`requirements.txt` alone (no test deps) is what actually ships in the production Docker image —
see `backend/Dockerfile`.

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

Run the background worker (digest, reminders, expiry, broadcasts, push):

```bash
python -m app.workers.scheduler
```

Interactive API docs once the API is running: `http://localhost:8000/docs`.

## Admin app / student app — local development

```bash
cd admin-app          # or: cd ghotlyai-job-portal
npm install
npx expo start
```

Set `EXPO_PUBLIC_API_URL` (e.g. in a `.env` file read by Expo, or inline before `expo start`) to
point at your running backend. Both apps need a custom EAS dev client, not Expo Go, since both
carry native modules (Razorpay Checkout, and the admin app's push/update-check native pieces)
Expo Go cannot load.

Type-check anytime with `npx tsc --noEmit`.

## Deploying to production

- **VPS** (Docker Compose, SSL, backups, monitoring) — the only supported path: `docs/DEPLOY.md`
- **Admin APK**: `docs/APP_RELEASE.md` (GitHub Actions builds it automatically)
- **Student APK**: `docs/APP_RELEASE_STUDENT.md` (same GitHub Actions approach)

## Where things are documented

- **Business rules, pricing, roadmap**: `Student_Job_Alert_Bot_Master_Plan.pdf`
- **Engineering conventions, data model, locked tech decisions**: `CLAUDE.md`
- **API**: `http://localhost:8000/docs` (Swagger) once the backend is running
- **VPS deployment runbook**: `docs/DEPLOY.md`
- **Admin app release runbook**: `docs/APP_RELEASE.md`
- **Student app release runbook**: `docs/APP_RELEASE_STUDENT.md`

## Status

Backend (bot, admin API, student API, workers, payments, AI resume parsing) and both apps are
built, tested (177 automated backend tests) and wired end to end, live in production on a
self-hosted VPS. The student app skips phone OTP entirely - a resume upload is the signup, with
Gemini extracting name/phone/email/education directly from it.
