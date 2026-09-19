# JobKatta — Student Job Alert App

Expo/TypeScript app giving students the same functionality as the Telegram bot (onboarding,
job feed, payment, support), talking to the **same backend** as the bot via new `/student/*`
API routes (see `backend/app/api/student/`). No second backend — same database, same business
logic.

Placeholder name/branding (`JobKatta`, green `#16A34A`) — trivially renamed by editing
`app.json`, `package.json` and `tailwind.config.js`.

## Requires a custom EAS dev client, not Expo Go

Phone auth (`@react-native-firebase/auth`) and the native Razorpay Checkout SDK
(`react-native-razorpay`) both need native modules Expo Go cannot load — same as `admin-app/`
already requires. Build a development client before running the app:

```bash
npm install
eas build --profile development --platform android
```

Install the resulting APK on a physical Android phone with a live SIM — phone-auth SMS
auto-verification cannot be tested in an emulator or Expo Go.

## Before this can run for real

1. **`eas init`** (as your Expo account) to create the EAS project and populate
   `app.json`'s `extra.eas.projectId` — not filled in yet, since that requires your login.
2. **Firebase project** (console.firebase.google.com): enable **Phone** sign-in under
   Authentication, then download:
   - `google-services.json` → place at the repo root of this folder (Android)
   - `GoogleService-Info.plist` → place at the repo root of this folder (iOS)
   - A **service account key** (Project Settings → Service accounts → Generate new private
     key) → set as `FIREBASE_SERVICE_ACCOUNT_JSON` in the **backend's** `.env` (the backend
     verifies the ID token server-side; see `backend/app/services/firebase_auth.py`).
3. **Razorpay**: the backend's existing `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` are reused for
   the Orders API (`backend/app/services/razorpay_orders.py`) — no new keys needed. In the
   Razorpay dashboard, make sure the webhook has the **`payment.captured`** event enabled
   alongside whatever `payment_link.*` events are already on (this is the app payment flow's
   defense-in-depth path, separate from the bot's Payment Links flow).
4. **Backend migrations**: run `alembic upgrade head` against the production DB before this
   app can log anyone in — migrations `0004_app_login_support` and `0005_razorpay_orders` add
   the columns this app's API depends on.
5. **Android Phone Number Hint** (auto-fill the number, zero typing): `lib/firebaseAuth.ts`'s
   `getPhoneNumberHint()` is currently a stub that always returns `null` — the login screen's
   manual entry field is what actually works today. Wiring a real implementation (Google
   Identity Services' Phone Number Hint API has no first-party Expo/RNFirebase wrapper yet) is
   the one upgrade needed to get the fully "just tap confirm" flow; everything else is unaffected.
6. **App icons/splash**: `assets/*.png` are placeholder green marks generated for this build,
   not final artwork — swap them before a real store listing.

## Structure

- `app/(auth)` — welcome, phone entry, OTP
- `app/(onboarding)` — name → district → resume (optional) → job types → categories, mirroring
  the Telegram bot's onboarding order
- `app/(tabs)` — Home (job feed, search + filter), Support, Profile
- `app/job/[id].tsx`, `app/filters.tsx`, `app/payment/checkout.tsx`
- `lib/api.ts` — typed client for every `/student/*` backend route
- `lib/firebaseAuth.ts` — phone OTP send/confirm
- `store/auth.ts` — SecureStore-backed session (same Zustand `persist` pattern as `admin-app/`)
