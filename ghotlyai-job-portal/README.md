# GhotlyAI Job Portal — Student Job Alert App

Expo/TypeScript app giving students the same functionality as the Telegram bot (onboarding,
job feed, payment, support), talking to the **same backend** as the bot via new `/student/*`
API routes (see `backend/app/api/student/`). No second backend — same database, same business
logic.

Same GhotlyAI brand as the admin app (ghost mascot, orange `#EA580C` accent), on a white-forward
in-app background. Internal identifiers (`slug`/`scheme` in `app.json`, npm package name) stay
`jobkatta` since they're tied to the already-created EAS project — only user-facing text/colors
changed.

## Sign-up: resume-first, no phone OTP

There is no login screen. A student uploads their resume; the backend runs it through Gemini
(the same parser the Telegram bot already uses) to extract full name, phone, email and
education, creates the account from that, and returns a session token immediately - no SMS, no
Firebase Auth, no waiting. If the extracted phone already belongs to an existing Telegram-bot
user, that account is recognized and reused as-is. If the resume has no phone (or the wrong
one), the very next screen asks for it as a plain typed field - still never OTP-verified, same
trust model the bot already has for whatever a user types into it.

This is a deliberate trade-off: no proof the phone typed/extracted actually belongs to the
person entering it. Acceptable here since it mirrors how much the bot already trusts, but worth
knowing if this ever needs a stronger identity guarantee later.

## Getting an installable APK

**Primary path — GitHub Actions** (no EAS build servers, no Expo login needed to trigger it):
`.github/workflows/build-student-apk.yml` builds a real signed release APK directly on a GitHub
runner, the same way `build-admin-apk.yml` does for the admin app. See
`docs/APP_RELEASE_STUDENT.md` for the one-time GitHub secrets setup and how to run it.

**Local/dev path**: the native Razorpay Checkout SDK (`react-native-razorpay`) needs a native
module Expo Go cannot load, so a plain `expo start` won't run this app - use an EAS dev client:

```bash
npm install
eas build --profile development --platform android
```

## Setup status

Done:
- EAS project created and linked (`app.json`'s `extra.eas.projectId`).
- Firebase project + `google-services.json` in place (used only for FCM push notifications now,
  not auth), GitHub Actions secrets added.

Still pending before this is fully live:
1. **Razorpay webhook**: confirm the **`payment.captured`** event is enabled in the Razorpay
   dashboard alongside whatever `payment_link.*` events are already on (the app payment flow's
   defense-in-depth path, separate from the bot's Payment Links flow) — the backend's existing
   `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` are reused as-is, no new keys needed.
2. **Backend migrations**: run `alembic upgrade head` against the production DB before this app
   can log anyone in — migrations `0004_app_login_support` through `0006_user_email` add the
   columns this app's API depends on.
3. **App icons/splash**: `assets/*.png` use the real GhostlyAI ghost mascot already, but the
   Android adaptive icon layers are the same ones the admin app uses — fine for now, revisit if
   the two apps ever need to look distinguishable in a launcher side-by-side.
4. **iOS**: `GoogleService-Info.plist` not provided yet — this app is Android-first for now.

## Structure

- `app/(auth)` — welcome, resume upload (this *is* signup)
- `app/(onboarding)` — confirm name/phone → district → job types → categories, mirroring the
  Telegram bot's onboarding order (resume itself was already captured at signup)
- `app/(tabs)` — Home (job feed, search + filter), Support, Profile
- `app/job/[id].tsx`, `app/filters.tsx`, `app/payment/checkout.tsx`
- `lib/api.ts` — typed client for every `/student/*` backend route
- `store/auth.ts` — SecureStore-backed session (same Zustand `persist` pattern as `admin-app/`)
