# Student Job Alert Bot — Master Context

Read this whole file before writing any code in this repo. It is the locked spec. If something
here is unclear or seems wrong, ask before deviating. Full business/product/technical spec lives in
`Student_Job_Alert_Bot_Master_Plan.pdf` (already summarized below) — treat this file as the
source of truth for engineering.

## PROJECT

"Student Job Alert Bot" — a paid job-alert service for students and freshers in Maharashtra, India.

- Students use a **Telegram bot**: they give full name, verified phone (contact share), district,
  resume (PDF/DOCX/photo parsed by Gemini), pick up to 3 job categories and job types.
- After onboarding they get a 3-day free trial, then pay Rs 99 for 30 days via **Razorpay Payment
  Links**.
- Admin uploads 500+ jobs per day from an **Admin Android app** (React Native + Expo).
- A worker checks every 2 minutes and sends each student a digest of NEW jobs that match their
  categories and job types, so a newly posted job reaches students within minutes (both Telegram
  and the app; formerly a fixed twice-daily 09:00/18:00 Telegram slot - changed 2026-09).
  Apply buttons go through a signed click-tracking redirect. Matching no longer considers
  district (the product isn't Maharashtra-only) - see BUSINESS RULES.
- Bot languages: Marathi (default), Hindi, English. All bot copy lives in one texts file.
- This is a JOB ALERT service, never a job guarantee. Only verified jobs with official apply links.

## LOCKED TECH STACK (do not change without asking)

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, pydantic-settings
- **Bot**: aiogram 3 (FSM with RedisStorage), webhook in production, polling for local dev
- **AI**: `google-genai` SDK, async client, model from env `GEMINI_MODEL` (default
  `gemini-3.8-flash`), structured JSON output with Pydantic `response_schema`; do not set
  `temperature` for Gemini 3 models
- **Payments**: Razorpay REST API via httpx (payment_links), webhook HMAC-SHA256 verification
- **Jobs**: separate worker process with APScheduler 3 (timezone Asia/Kolkata)
- **Storage**: PostgreSQL 16, Redis 7, resume files on a Docker volume at `/data/resumes`
- **Admin auth**: JWT (PyJWT, HS256), bcrypt, roles: `owner` | `uploader`
- **Admin app**: Expo (latest SDK), TypeScript, expo-router, NativeWind, Reanimated, Moti, Gorhom
  Bottom Sheet, Lottie, FlashList, TanStack Query, Zustand, react-hook-form + zod, axios,
  expo-secure-store
- **Deploy**: Docker Compose (nginx, api, worker, postgres, redis) on a single Ubuntu 24.04 VPS,
  Let's Encrypt

## DATA MODEL (tables — see backend/app/db/models.py for the real definitions)

```
users(id, telegram_id unique, username, full_name, phone, district, language, job_types jsonb,
      status onboarding|active|blocked|bot_blocked, trial_ends_at, last_digest_at, last_teaser_at,
      reminder_sent_for, created_at, updated_at)
profiles(id, user_id unique, education, course, skills jsonb, experience_years, summary,
         resume_path, resume_mime, parsed_json jsonb, updated_at)
categories(id, slug unique, name, name_mr, name_hi, is_active, sort_order)
user_categories(user_id, category_id) PK both
admins(id, name, email unique, password_hash, role, is_active, created_at)
jobs(id, category_id, admin_id, title, company, qualification, district NULL=anywhere, location_text,
     job_type govt|private|internship|wfh, salary, description, apply_link, last_date,
     status active|expired|deleted, fingerprint unique sha256(title|company|apply_link), created_at)
job_deliveries(id, job_id, user_id, sent_at, clicked_at) unique(job_id, user_id)
subscriptions(id, user_id, start_at, end_at, source payment|admin, created_at)
payments(id, user_id, subscription_id, reference_id unique, razorpay_link_id unique,
         razorpay_payment_id, short_url, amount_paise, status created|paid|expired, expires_at,
         paid_at, created_at)
app_settings(key pk, value jsonb): price_inr=99, subscription_days=30, trial_days=3,
             digest_max_jobs=10, max_categories=3, teaser_every_hours=48
broadcasts(id, admin_id, text, audience, category_id, total, sent, failed, status, created_at)
```

## BUSINESS RULES (must be exact)

- Access = any `subscription.end_at > now` OR `trial_ends_at > now`. Trial only once per user.
- Extending a subscription adds days after the current paid end if it is in the future, else from
  now.
- Matching: `job.status='active'` AND category in user's categories AND (user.job_types empty OR
  job.job_type in user.job_types) AND (last_date IS NULL OR last_date >= today IST) AND created
  within last 7 days AND not already in job_deliveries for this user. Newest first. District plays
  no part in matching (product is not Maharashtra-only).
- Digest: max 10 jobs, 5 jobs per Telegram message, ~20 messages/sec, handle RetryAfter,
  Forbidden -> mark user bot_blocked. Delete delivery rows if nothing was sent. Runs on a
  frequent interval (every 2 minutes), not fixed daily slots.
- Expired users get a locked teaser with match count at most once per 48h.
- Payment webhook must be idempotent, verify signature and full amount.
- The Telegram bot still collects/validates district (35 Maharashtra districts, new names,
  aliases for old names/Devanagari) - the student app does not collect district at all.
- All user-provided text inserted in HTML messages must be `html.escape()`'d.
- Datetimes stored as timezone-aware UTC; displayed in IST (DD-MM-YYYY).
- Category slugs never change (matching + Excel upload depend on them); 21 seeded categories.

## CODE CONVENTIONS

- Folder layout: `backend/app/{config.py, main.py, db/, bot/, services/, api/, workers/, scripts/}`.
- Business logic lives in `services/`, never inside handlers or routes.
- Type hints everywhere, small functions, docstrings only where logic is non-obvious.
- No secrets in code. Read everything from settings. Keep `.env.example` updated.
- Every external call (Gemini, Razorpay, Telegram) has error handling and logging, never crashes
  the bot or worker.
- Write pytest tests for services (SQLite via aiosqlite is fine for unit tests).
- Admin app: `admin-app/` is a separate Expo TypeScript project; API base URL from
  `EXPO_PUBLIC_API_URL`.

## HOW WE WORK

Implement one task/prompt at a time, completely, with working code. Do not invent features beyond
what's specified. Confirm scope in a short plan first for anything ambiguous, otherwise just build
it — the spec above (and the PDF) already answers almost everything. After each task: note files
changed, how to run/test it, and anything that still needs a real secret (Bot token, Gemini key,
Razorpay keys, VPS/domain) to actually go live.
