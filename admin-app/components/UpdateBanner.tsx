import { MotiView, AnimatePresence } from "moti";
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Linking, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { downloadAndInstallApk, type InstallStage } from "@/lib/apkInstall";
import { checkForUpdate, type AvailableUpdate } from "@/lib/updateCheck";

const RECHECK_MS = 6 * 60 * 60 * 1000; // 6h - plus once on every cold app open

type Phase = "idle" | "downloading" | "opening-installer" | "waiting-for-install" | "error";

/** Checks GitHub Releases for a newer APK on app open (and every few hours while it stays
 * open), and shows a persistent bottom banner so an update is never just a link someone has to
 * remember to go back and re-download - tapping it downloads and hands straight to the Android
 * installer. Dismissing it for this session doesn't stop the app from re-showing it on the
 * next cold open (state isn't persisted on purpose - a real update available is worth repeating).
 *
 * Every phase is shown explicitly (not just a toast that can be missed) because "tap update,
 * then nothing seems to happen" is exactly the failure mode this needs to avoid - the banner
 * always says which of downloading / handing off to the installer / erroring it's in, and an
 * error always keeps a "open in browser instead" escape hatch that's guaranteed to work (it's
 * the same manual flow this replaces). */
export function UpdateBanner() {
  const insets = useSafeAreaInsets();
  const [update, setUpdate] = useState<AvailableUpdate | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [errorText, setErrorText] = useState("");
  const checking = useRef(false);

  useEffect(() => {
    const check = async () => {
      if (checking.current) return;
      checking.current = true;
      try {
        const found = await checkForUpdate();
        setUpdate((current) => found ?? current);
      } finally {
        checking.current = false;
      }
    };
    check();
    const interval = setInterval(check, RECHECK_MS);
    return () => clearInterval(interval);
  }, []);

  if (!update || dismissed) return null;

  const install = async () => {
    setPhase("downloading");
    setProgress(0);
    setErrorText("");
    try {
      await downloadAndInstallApk(update.apkUrl, update.htmlUrl, setProgress, (stage: InstallStage) =>
        setPhase(stage)
      );
      // No error thrown means the installer intent launched successfully - Android now shows
      // its own system dialog on top of the app. There's nothing more this screen can observe
      // (we're not told whether the person taps Install), so this is the last state we set.
      setPhase("waiting-for-install");
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : "Update failed");
      setPhase("error");
    }
  };

  const openInBrowser = () => Linking.openURL(update.htmlUrl);

  return (
    <AnimatePresence>
      <MotiView
        from={{ translateY: 80, opacity: 0 }}
        animate={{ translateY: 0, opacity: 1 }}
        exit={{ translateY: 80, opacity: 0 }}
        transition={{ type: "timing", duration: 250 }}
        className="absolute left-4 right-4 bg-ink rounded-2xl px-4 py-3.5"
        style={{ bottom: insets.bottom + 76, zIndex: 150 }}
      >
        {phase === "downloading" || phase === "opening-installer" ? (
          <View>
            <View className="flex-row items-center mb-2">
              <ActivityIndicator color="#FFFFFF" size="small" />
              <Text className="text-white text-sm font-semibold ml-2">
                {phase === "downloading"
                  ? `Downloading update… ${Math.round(progress * 100)}%`
                  : "Opening installer…"}
              </Text>
            </View>
            <View className="h-1.5 rounded-full bg-white/20 overflow-hidden">
              <View
                className="h-full bg-brand rounded-full"
                style={{ width: `${phase === "opening-installer" ? 100 : Math.max(4, progress * 100)}%` }}
              />
            </View>
          </View>
        ) : phase === "waiting-for-install" ? (
          <View className="flex-row items-center">
            <Text style={{ fontSize: 20 }} className="mr-2">
              📲
            </Text>
            <View className="flex-1 mr-2">
              <Text className="text-white text-[15px] font-bold">Installer opened</Text>
              <Text className="text-white/70 text-xs mt-0.5">
                Look for Android's "Install" prompt - it may be behind this screen
              </Text>
            </View>
            <Pressable onPress={() => setDismissed(true)} hitSlop={8} className="px-1.5 py-1">
              <Text className="text-white/60 text-sm font-bold">✕</Text>
            </Pressable>
          </View>
        ) : phase === "error" ? (
          <View>
            <View className="flex-row items-start mb-2">
              <Text style={{ fontSize: 20 }} className="mr-2">
                ⚠️
              </Text>
              <View className="flex-1">
                <Text className="text-white text-[15px] font-bold">Couldn't install automatically</Text>
                <Text className="text-white/70 text-xs mt-0.5">{errorText}</Text>
              </View>
              <Pressable onPress={() => setDismissed(true)} hitSlop={8} className="px-1.5 py-1">
                <Text className="text-white/60 text-sm font-bold">✕</Text>
              </Pressable>
            </View>
            <View className="flex-row">
              <Pressable onPress={openInBrowser} className="bg-brand rounded-full px-3.5 py-2 mr-2">
                <Text className="text-white text-xs font-bold">Open download page</Text>
              </Pressable>
              <Pressable onPress={install} className="bg-white/15 rounded-full px-3.5 py-2">
                <Text className="text-white text-xs font-bold">Try again</Text>
              </Pressable>
            </View>
          </View>
        ) : (
          <View className="flex-row items-center">
            <Text style={{ fontSize: 20 }} className="mr-2">
              🚀
            </Text>
            <View className="flex-1 mr-2">
              <Text className="text-white text-[15px] font-bold">Update available — v{update.version}</Text>
              <Text className="text-white/70 text-xs mt-0.5">Tap to download and install</Text>
            </View>
            <Pressable onPress={install} className="bg-brand rounded-full px-3.5 py-2 mr-1">
              <Text className="text-white text-xs font-bold">Update</Text>
            </Pressable>
            <Pressable onPress={() => setDismissed(true)} hitSlop={8} className="px-1.5 py-1">
              <Text className="text-white/60 text-sm font-bold">✕</Text>
            </Pressable>
          </View>
        )}
      </MotiView>
    </AnimatePresence>
  );
}
