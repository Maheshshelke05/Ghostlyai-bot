/** Downloads a newer APK and hands it straight to the Android package installer, so an update
 * no longer means "open the browser, find the release, download, then open Downloads".
 *
 * Uses expo-file-system's legacy API deliberately: `getContentUriAsync` wraps a `file://` path
 * in a `content://` one served by expo-file-system's own registered FileProvider - required
 * because Android 7+ (API 24+) throws FileUriExposedException if you hand a raw file:// URI to
 * another app's intent (here, the system package installer).
 */
import * as IntentLauncher from "expo-intent-launcher";
import { cacheDirectory, createDownloadResumable, deleteAsync, getContentUriAsync } from "expo-file-system/legacy";
import { Linking, Platform } from "react-native";

const FLAG_GRANT_READ_URI_PERMISSION = 1;

export class ApkInstallError extends Error {}

export type InstallStage = "downloading" | "opening-installer";

/** iOS can't sideload APKs at all - opens the release page instead so there's still a next
 * step, rather than doing nothing. Android does the real download + install-intent flow. */
export async function downloadAndInstallApk(
  apkUrl: string,
  releasePageUrl: string,
  onProgress?: (fraction: number) => void,
  onStage?: (stage: InstallStage) => void
): Promise<void> {
  if (Platform.OS !== "android") {
    await Linking.openURL(releasePageUrl);
    return;
  }
  if (!cacheDirectory) {
    throw new ApkInstallError("No writable cache directory available on this device");
  }

  // Every update uses the same filename. If a PREVIOUS attempt (an older version, or one that
  // got interrupted) left a file here, a resumable download would try to resume from those
  // stale bytes - which belong to different content - producing a corrupted APK that the
  // installer silently rejects. Always start clean instead of resuming.
  const destination = `${cacheDirectory}job-alert-admin-update.apk`;
  try {
    await deleteAsync(destination, { idempotent: true });
  } catch {
    // best-effort cleanup; a failed delete isn't worth aborting the update over
  }

  onStage?.("downloading");
  const downloadable = createDownloadResumable(apkUrl, destination, {}, (progress) => {
    if (progress.totalBytesExpectedToWrite > 0) {
      onProgress?.(progress.totalBytesWritten / progress.totalBytesExpectedToWrite);
    }
  });

  let result;
  try {
    // Freshly created above with the stale destination file already deleted, so this always
    // does a full download - it can never silently "resume" from a different version's bytes.
    result = await downloadable.downloadAsync();
  } catch (err) {
    throw new ApkInstallError(
      err instanceof Error ? `Download failed: ${err.message}` : "Download failed"
    );
  }
  if (!result?.uri || (result.status && result.status >= 400)) {
    throw new ApkInstallError(`Download did not complete (server said ${result?.status ?? "no response"})`);
  }

  onStage?.("opening-installer");
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
    throw new ApkInstallError(
      err instanceof Error ? `Could not open the installer: ${err.message}` : "Could not open the installer"
    );
  }
}
