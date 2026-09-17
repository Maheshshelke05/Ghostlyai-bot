/** Checks GitHub Releases for a newer APK build than the one currently running, and can
 * download + launch the Android installer for it - so "a new update came out" no longer means
 * manually re-opening the release link every time.
 *
 * How the running build's own number is known: the CI workflow bakes
 * `EXPO_PUBLIC_BUILD_NUMBER` (GitHub's run_number) into the JS bundle at build time, and every
 * release tag is `admin-app-v<version>-<run_number>` - so comparing the trailing number in the
 * latest release's tag against this constant tells us if a newer build exists. This repo is
 * public, so the releases list is fetched unauthenticated (no token shipped in the app).
 */
const REPO = "Maheshshelke05/Ghostlyai-bot";
const RELEASES_URL = `https://api.github.com/repos/${REPO}/releases?per_page=10`;

export const CURRENT_BUILD_NUMBER = Number(process.env.EXPO_PUBLIC_BUILD_NUMBER ?? 0);

export interface AvailableUpdate {
  buildNumber: number;
  version: string;
  tagName: string;
  htmlUrl: string;
  apkUrl: string;
}

function parseBuildNumber(tagName: string): number | null {
  const m = /-(\d+)$/.exec(tagName);
  return m ? Number(m[1]) : null;
}

export async function checkForUpdate(): Promise<AvailableUpdate | null> {
  let releases: any[];
  try {
    const res = await fetch(RELEASES_URL, { headers: { Accept: "application/vnd.github+json" } });
    if (!res.ok) return null;
    releases = await res.json();
  } catch {
    return null; // offline / GitHub unreachable - silently skip, this is a nice-to-have check
  }

  for (const release of releases) {
    if (typeof release?.tag_name !== "string" || !release.tag_name.startsWith("admin-app-v")) continue;
    const buildNumber = parseBuildNumber(release.tag_name);
    if (buildNumber === null) continue;

    const apkAsset = (release.assets ?? []).find((a: any) => typeof a?.name === "string" && a.name.endsWith(".apk"));
    if (!apkAsset) continue; // a release still mid-upload / asset missing - wait for the next one

    if (CURRENT_BUILD_NUMBER > 0 && buildNumber > CURRENT_BUILD_NUMBER) {
      return {
        buildNumber,
        version: release.tag_name.replace(/^admin-app-v/, "").replace(/-\d+$/, ""),
        tagName: release.tag_name,
        htmlUrl: release.html_url,
        apkUrl: apkAsset.browser_download_url,
      };
    }
    // Releases are returned newest-first; the first one with a real build number is the
    // latest, so once it's not newer than us, nothing older can be either.
    break;
  }
  return null;
}
