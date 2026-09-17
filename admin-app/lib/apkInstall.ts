/** Downloads a newer APK and hands it straight to the Android package installer, so an update
 * no longer means "open the browser, find the release, download, then open Downloads".
 *
 * Uses expo-file-system's legacy API deliberately: `getContentUriAsync` wraps a `file://` path
 * in a `content://` one served by expo-file-system's own registered FileProvider - required
 * because Android 7+ (API 24+) throws FileUriExposedException if you hand a raw file:// URI to
 * another app's intent (here, the system package installer).
 */
import * as IntentLauncher from "expo-intent-launcher";
import { cacheDirectory, createDownloadResumable, getContentUriAsync } from "expo-file-system/legacy";
import { Linking, Platform } from "react-native";

const FLAG_GRANT_READ_URI_PERMISSION = 1;

export class ApkInstallError extends Error {}

/** iOS can't sideload APKs at all - opens the release page instead so there's still a next
 * step, rather than doing nothing. Android does the real download + install-intent flow. */
export async function downloadAndInstallApk(
  apkUrl: string,
  releasePageUrl: string,
  onProgress?: (fraction: number) => void
): Promise<void> {
  if (Platform.OS !== "android") {
    await Linking.openURL(releasePageUrl);
    return;
  }
  if (!cacheDirectory) {
    throw new ApkInstallError("No writable cache directory available on this device");
  }

  const destination = `${cacheDirectory}job-alert-admin-update.apk`;
  const downloadable = createDownloadResumable(apkUrl, destination, {}, (progress) => {
    if (progress.totalBytesExpectedToWrite > 0) {
      onProgress?.(progress.totalBytesWritten / progress.totalBytesExpectedToWrite);
    }
  });

  let result;
  try {
    result = await downloadable.downloadAsync();
  } catch (err) {
    throw new ApkInstallError(err instanceof Error ? err.message : "Download failed");
  }
  if (!result?.uri) {
    throw new ApkInstallError("Download did not complete");
  }

  const contentUri = await getContentUriAsync(result.uri);
  try {
    await IntentLauncher.startActivityAsync("android.intent.action.VIEW", {
      data: contentUri,
      flags: FLAG_GRANT_READ_URI_PERMISSION,
      type: "application/vnd.android.package-archive",
    });
  } catch (err) {
    // Some OEM launchers/ROMs reject the intent outright (rare) - the APK is downloaded either
    // way, so at least point at the release page as a manual fallback instead of leaving the
    // admin stuck with nothing.
    throw new ApkInstallError(err instanceof Error ? err.message : "Could not open the installer");
  }
}
