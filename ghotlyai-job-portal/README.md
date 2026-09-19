# JobKatta — Student Job Alert App

Expo/TypeScript app giving students the same functionality as the Telegram bot (onboarding,
job feed, payment, support), talking to the **same backend** as the bot via new `/student/*`
API routes (see `backend/app/api/student/`). No second backend — same database, same business
logic.

Placeholder name/branding (`JobKatta`, green `#16A34A`) — trivially renamed by editing
`app.json`, `package.json` and `tailwind.config.js`.

## Getting an installable APK

**Primary path — GitHub Actions** (no EAS build servers, no Expo login needed to trigger it):
`.github/workflows/build-student-apk.yml` builds a real signed release APK directly on a GitHub
runner, the same way `build-admin-apk.yml` does for the admin app. See
`docs/APP_RELEASE_STUDENT.md` for the one-time GitHub secrets setup and how to run it.

**Local/dev path — EAS dev client**: needed only for live Metro reloading during development.
Phone auth (`@react-native-firebase/auth`) and the native Razorpay Checkout SDK
(`react-native-razorpay`) both need native modules Expo Go cannot load, so a plain `expo start`
won't work either way.

```bash
npm install
eas build --profile development --platform android
```

Either way, install the resulting APK on a physical Android phone with a live SIM — phone-auth
SMS auto-verification cannot be tested in an emulator or Expo Go.

## Setup status

Done:
- EAS project created and linked (`app.json`'s `extra.eas.projectId`).
- Firebase: Phone sign-in enabled, `google-services.json` in place, service account key wired
  into the backend's `FIREBASE_SERVICE_ACCOUNT_JSON`, GitHub Actions secrets added.

Still pending before this is fully live:
1. **Razorpay webhook**: confirm the **`payment.captured`** event is enabled in the Razorpay
   dashboard alongside whatever `payment_link.*` events are already on (the app payment flow's
   defense-in-depth path, separate from the bot's Payment Links flow) — the backend's existing
   `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` are reused as-is, no new keys needed.
2. **Backend migrations**: run `alembic upgrade head` against the production DB before this app
   can log anyone in — migrations `0004_app_login_support` and `0005_razorpay_orders` add the
   columns this app's API depends on.
3. **Firebase SHA fingerprints**: add this app's release keystore's SHA-1/SHA-256 to the
   Firebase console (`com.jobalertbot.student` app → Add fingerprint) for reliable phone-auth
   auto-verification — see `docs/APP_RELEASE_STUDENT.md`.
4. **Android Phone Number Hint** (auto-fill the number, zero typing): `lib/firebaseAuth.ts`'s
   `getPhoneNumberHint()` is currently a stub that always returns `null` — the login screen's
   manual entry field is what actually works today. Wiring a real implementation (Google
   Identity Services' Phone Number Hint API has no first-party Expo/RNFirebase wrapper yet) is
   the one upgrade needed to get the fully "just tap confirm" flow; everything else is unaffected.
5. **App icons/splash**: `assets/*.png` are placeholder green marks generated for this build,
   not final artwork — swap them before a real store listing.
6. **iOS**: `GoogleService-Info.plist` not provided yet — this app is Android-first for now.

## Structure

- `app/(auth)` — welcome, phone entry, OTP
- `app/(onboarding)` — name → district → resume (optional) → job types → categories, mirroring
  the Telegram bot's onboarding order
- `app/(tabs)` — Home (job feed, search + filter), Support, Profile
- `app/job/[id].tsx`, `app/filters.tsx`, `app/payment/checkout.tsx`
- `lib/api.ts` — typed client for every `/student/*` backend route
- `lib/firebaseAuth.ts` — phone OTP send/confirm
- `store/auth.ts` — SecureStore-backed session (same Zustand `persist` pattern as `admin-app/`)
