# Building and releasing the Admin app

The admin app (`admin-app/`) is an Expo/React Native app. You don't need the Play Store to use
it internally — EAS Build produces an installable `.apk` you can send directly to a phone.

## One-time setup

```bash
cd admin-app
npm install -g eas-cli
eas login
eas build:configure   # links this project to your Expo account (creates a project id)
```

## Point the app at your backend

`eas.json` build profiles set `EXPO_PUBLIC_API_URL` per environment:
- `preview` / `production` → `https://api.ghotlyai.in`
- `development` → `http://localhost:8000` (for use with `expo start` against a local backend)

## Build an APK for internal testing

```bash
cd admin-app
eas build --platform android --profile preview
```

This uploads the project to EAS's build servers and prints a URL when done. Open that URL on
the phone (or scan the QR code EAS shows) to download and install the APK. Android will ask you
to allow installs from unknown sources the first time — that's expected for a non-Play-Store APK.

## Development client (optional, for local iteration)

```bash
eas build --platform android --profile development
npx expo start --dev-client
```

## Production build (Play Store / final release)

```bash
eas build --platform android --profile production
```

This produces an `.aab` app bundle, the format the Play Store expects. Only build this once
the app is genuinely ready for a store listing — for internal admin use, `preview` APKs are
enough indefinitely.

## Updating the app after code changes

1. Bump `"version"` in `admin-app/app.json` for any user-facing release.
2. Re-run the same `eas build` command for the profile you need.
3. Distribute the new APK the same way (link/QR from the EAS build page).

There is no auto-update for native-code changes (new libraries, permissions) — those always need
a fresh APK install. For JS-only changes, EAS Update (`eas update`) can push instantly without a
new APK, but that's a Phase 2 optimization, not required for launch.

## Troubleshooting

- **Blank screen on launch**: check `EXPO_PUBLIC_API_URL` is reachable from the phone (not
  `localhost`, unless using an emulator with port forwarding) and that the backend's CORS/HTTPS
  are set up correctly.
- **Login fails but the API is reachable**: confirm an admin account exists — run
  `docker compose exec api python -m app.scripts.create_admin` on the server.
- **Native module crash after adding a package**: `npx expo install <package>` (not plain
  `npm install`) keeps native dependency versions aligned with the installed Expo SDK.
