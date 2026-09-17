import { LinearGradient } from "expo-linear-gradient";
import { MotiView } from "moti";
import { useEffect } from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import { Easing } from "react-native-reanimated";

const MARK = 280;
const AURA = 600;

/**
 * Launch sequence built from separate, identically-framed logo layers so each part can
 * move on its own and still land in exact registration:
 * aura fades in and slowly turns -> ghost rises in -> crown drops onto its head ->
 * namam appears -> briefcase badge pops -> wordmark slides up, with the whole mark floating.
 */
export function AnimatedSplash({ onFinish }: { onFinish: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onFinish, 2800);
    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <View style={StyleSheet.absoluteFill}>
      <LinearGradient colors={["#FB923C", "#EA580C"]} style={StyleSheet.absoluteFill} />

      <View style={styles.center}>
        <View style={styles.markArea}>
          <MotiView
            from={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "timing", duration: 900 }}
            style={styles.aura}
          >
            <MotiView
              from={{ rotate: "0deg" }}
              animate={{ rotate: "360deg" }}
              transition={{ type: "timing", duration: 26000, loop: true, repeatReverse: false, easing: Easing.linear }}
              style={StyleSheet.absoluteFill}
            >
              <Image source={require("../assets/splash-aura.png")} style={styles.fill} />
            </MotiView>
          </MotiView>

          {/* gentle ghost float for the whole mark once it has landed */}
          <MotiView
            from={{ translateY: 0 }}
            animate={{ translateY: -9 }}
            transition={{ type: "timing", duration: 1300, loop: true, delay: 900, easing: Easing.inOut(Easing.quad) }}
            style={styles.mark}
          >
            <MotiView
              from={{ opacity: 0, scale: 0.55, translateY: 50 }}
              animate={{ opacity: 1, scale: 1, translateY: 0 }}
              transition={{ type: "spring", damping: 12, stiffness: 120 }}
              style={StyleSheet.absoluteFill}
            >
              <Image source={require("../assets/splash-ghost.png")} style={styles.fill} />
            </MotiView>

            <MotiView
              from={{ opacity: 0, scale: 0.2 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", damping: 11, stiffness: 150, delay: 950 }}
              style={StyleSheet.absoluteFill}
            >
              <Image source={require("../assets/splash-namam.png")} style={styles.fill} />
            </MotiView>

            <MotiView
              from={{ opacity: 0, translateY: -170 }}
              animate={{ opacity: 1, translateY: 0 }}
              transition={{
                opacity: { type: "timing", duration: 200, delay: 450 },
                translateY: { type: "spring", damping: 9, stiffness: 110, delay: 450 },
              }}
              style={StyleSheet.absoluteFill}
            >
              <Image source={require("../assets/splash-crown.png")} style={styles.fill} />
            </MotiView>

            <MotiView
              from={{ opacity: 0, scale: 0, rotate: "-25deg" }}
              animate={{ opacity: 1, scale: 1, rotate: "0deg" }}
              transition={{ type: "spring", damping: 9, stiffness: 160, delay: 1250 }}
              style={StyleSheet.absoluteFill}
            >
              <Image source={require("../assets/splash-badge.png")} style={styles.fill} />
            </MotiView>
          </MotiView>
        </View>

        <MotiView
          from={{ opacity: 0, translateY: 18 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 550, delay: 1450 }}
          style={styles.wordmark}
        >
          <Text style={styles.brand}>
            Ghostly<Text style={styles.brandAccent}> AI</Text>
          </Text>
          <Text style={styles.tagline}>Job Alert Admin</Text>
        </MotiView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  markArea: { width: AURA, height: MARK + 40, alignItems: "center", justifyContent: "center" },
  aura: { position: "absolute", width: AURA, height: AURA },
  mark: { width: MARK, height: MARK },
  fill: { width: "100%", height: "100%" },
  wordmark: { alignItems: "center", marginTop: 6 },
  brand: { fontSize: 34, fontWeight: "800", color: "#FFFFFF", letterSpacing: 0.3 },
  brandAccent: { color: "#0F172A" },
  tagline: { fontSize: 13, fontWeight: "600", color: "rgba(255,255,255,0.85)", marginTop: 2, letterSpacing: 1.2 },
});
