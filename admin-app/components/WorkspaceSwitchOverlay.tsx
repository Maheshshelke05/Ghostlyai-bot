import { LinearGradient } from "expo-linear-gradient";
import { MotiView } from "moti";
import { useEffect, useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import { Easing } from "react-native-reanimated";

import { useAppModeStore, type AppMode } from "@/store/appMode";

const DURATION_MS = 10_000;

const LABEL: Record<AppMode, { emoji: string; name: string }> = {
  jobalert: { emoji: "🏠", name: "Job Alert Bot" },
  ghostly: { emoji: "👻", name: "GhostlyAI.in" },
};

/**
 * Full-screen branded transition shown while switching workspaces (Job Alert Bot <->
 * GhostlyAI.in). Runs for a fixed 10s, then flips the app's mode - the old workspace's screens
 * stay mounted underneath this whole overlay (nothing unmounts, nothing re-fetches, no risk of
 * either workspace erroring mid-switch), and the target workspace only mounts once the overlay
 * lifts, the same as opening it fresh.
 *
 * This is the ONLY place `endSwitch()` (which actually flips `mode`) is called, so every
 * "switch workspace" button goes through the same overlay by calling `beginSwitch()` instead
 * of setting mode directly.
 */
export function WorkspaceSwitchOverlay() {
  const switchingTo = useAppModeStore((s) => s.switchingTo);
  const endSwitch = useAppModeStore((s) => s.endSwitch);

  // Remounts (key change) below reset the progress-bar animation cleanly each time this fires.
  if (!switchingTo) return null;
  return <Overlay key={switchingTo} target={switchingTo} onDone={endSwitch} />;
}

function Overlay({ target, onDone }: { target: AppMode; onDone: () => void }) {
  const [dots, setDots] = useState(0);
  const label = LABEL[target];

  useEffect(() => {
    const finishTimer = setTimeout(onDone, DURATION_MS);
    const dotTimer = setInterval(() => setDots((d) => (d + 1) % 4), 450);
    return () => {
      clearTimeout(finishTimer);
      clearInterval(dotTimer);
    };
  }, [onDone]);

  return (
    // zIndex is explicit (not just JSX order) because React Native compares it across siblings
    // regardless of render order - without it this could end up painted behind the Stack's
    // screens, or behind OfflineBanner (200) / UpdateBanner (150), which must never happen here.
    <View style={[StyleSheet.absoluteFill, { zIndex: 500 }]} pointerEvents="auto">
      <LinearGradient colors={["#FB923C", "#EA580C"]} style={StyleSheet.absoluteFill} />

      <View style={styles.center}>
        <View style={styles.markArea}>
          <MotiView
            from={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "timing", duration: 700 }}
            style={styles.aura}
          >
            <MotiView
              from={{ rotate: "0deg" }}
              animate={{ rotate: "360deg" }}
              transition={{ type: "timing", duration: 6000, loop: true, repeatReverse: false, easing: Easing.linear }}
              style={StyleSheet.absoluteFill}
            >
              <Image source={require("../assets/splash-aura.png")} style={styles.fill} />
            </MotiView>
          </MotiView>

          <MotiView
            from={{ translateY: 0 }}
            animate={{ translateY: -10 }}
            transition={{ type: "timing", duration: 900, loop: true, easing: Easing.inOut(Easing.quad) }}
            style={styles.mark}
          >
            <MotiView
              from={{ opacity: 0, scale: 0.6, translateY: 30 }}
              animate={{ opacity: 1, scale: 1, translateY: 0 }}
              transition={{ type: "spring", damping: 12, stiffness: 140 }}
            >
              <Image source={require("../assets/splash-ghost.png")} style={styles.fill} />
            </MotiView>
          </MotiView>
        </View>

        <MotiView
          from={{ opacity: 0, translateY: 12 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 500, delay: 200 }}
        >
          <Text style={styles.title}>Switching workspace</Text>
          <Text style={styles.subtitle}>
            {label.emoji} {label.name}
            {".".repeat(dots)}
          </Text>
        </MotiView>

        <View style={styles.trackWrap}>
          <View style={styles.track}>
            <MotiView
              from={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ type: "timing", duration: DURATION_MS, easing: Easing.out(Easing.cubic) }}
              style={styles.fillBar}
            />
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  markArea: { width: 160, height: 160, alignItems: "center", justifyContent: "center", marginBottom: 28 },
  aura: { position: "absolute", width: 160, height: 160 },
  mark: { width: 100, height: 100 },
  fill: { width: "100%", height: "100%", resizeMode: "contain" },
  title: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "800",
    textAlign: "center",
    letterSpacing: 0.2,
  },
  subtitle: {
    color: "#FFF1E8",
    fontSize: 15,
    fontWeight: "600",
    textAlign: "center",
    marginTop: 6,
    minWidth: 220,
  },
  trackWrap: { width: 200, marginTop: 32 },
  track: {
    height: 6,
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.25)",
    overflow: "hidden",
  },
  fillBar: {
    height: "100%",
    borderRadius: 999,
    backgroundColor: "#FFFFFF",
  },
});
