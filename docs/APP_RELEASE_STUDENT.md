# Building and releasing the JobKatta (student) app

`ghotlyai-job-portal/` is an Expo/React Native app. `.github/workflows/build-student-apk.yml`
builds a real, installable, signed `.apk` **directly on a GitHub Actions runner** (prebuild +
`./gradlew assembleRelease`) — no EAS build servers, no Expo login needed to trigger it.

## One-time setup: add these GitHub repository secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | What it is |
|---|---|
| `STUDENT_GOOGLE_SERVICES_JSON_BASE64` | The Firebase `google-services.json` for `com.jobalertbot.student` (used for push notifications only, not auth), base64-encoded on one line |
| `STUDENT_ANDROID_RELEASE_KEYSTORE_BASE64` | The app's release signing keystore, base64-encoded on one line |
| `STUDENT_ANDROID_RELEASE_KEYSTORE_PASSWORD` | That keystore's store/key password |
| `STUDENT_ANDROID_RELEASE_KEY_ALIAS` | `jobkatta-release` |

These are separate from the admin app's `GOOGLE_SERVICES_JSON_BASE64`/`ANDROID_RELEASE_*`
secrets on purpose — each app should have its own signing identity, never shared.

To base64-encode a file yourself later (e.g. after rotating the keystore):

```bash
base64 -w0 google-services.json   # Linux/Git Bash
# or, PowerShell:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("google-services.json"))
```

## Running it

- **On demand**: repo → **Actions** tab → **Build Student App APK** → **Run workflow**.
- **Automatically**: any push to `main` touching `ghotlyai-job-portal/**`.

**Getting the APK afterward**: the finished run's **Summary** page has a
`jobkatta-v<version>-<run_number>` artifact (zip containing the APK, 90-day retention), and the
workflow also publishes a GitHub **Release** with the APK attached directly — no login needed to
download either.

## Why arm64-v8a only (not also armeabi-v7a like the admin app)

The workflow's "Tune Gradle build" step sets `reactNativeArchitectures=arm64-v8a` — dropping
32-bit ARM support entirely, more aggressive than the admin app's arm64+armeabi-v7a. This app
carries the native Razorpay Checkout SDK on top of the same RN/Expo base, and virtually every
phone a student owns today is 64-bit, so there's no real install base being cut off. This is the
main lever keeping the APK near the ~50-60MB target — if a future measurement shows it's still
too large, the next lever (not yet applied, since it carries real breakage risk for native
modules without carefully written ProGuard rules) would be `minifyEnabled true` +
`shrinkResources true` on the release build type.

## Point the app at your backend

`EXPO_PUBLIC_API_URL` is set to `https://api.ghotlyai.in` directly in the workflow's `env:`
block (same value for every build, since this app has no separate "preview" vs "production"
profile the way the admin app's `eas.json` does). Change it there if the backend URL ever moves.

## Updating the app after code changes

1. Bump `"version"` in `ghotlyai-job-portal/app.json` for a user-facing release.
2. Push to `main` (or run the workflow manually) — a new signed APK comes out the other end,
   already installable as an update over an existing install since the signing identity is
   stable across builds.
