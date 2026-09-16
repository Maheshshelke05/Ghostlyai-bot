import { LinearGradient } from "expo-linear-gradient";
import { MotiView } from "moti";
import { useEffect } from "react";
import { Image, StyleSheet, Text, View } from "react-native";

/**
 * Takes over from the native splash so the launch has motion instead of a static
 * frame: the mark scales up behind an expanding glow ring, then the wordmark rises
 * into place. onFinish fires once the sequence has had time to play.
 */
export function AnimatedSplash({ onFinish }: { onFinish: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onFinish, 1900);
    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <View style={StyleSheet.absoluteFill}>
      <LinearGradient
        colors={["#F8CB46", "#FFDE86", "#F8CB46"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />

      <View className="flex-1 items-center justify-center">
        <View className="items-center justify-center">
          {/* glow ring pulsing out from behind the mark */}
          <MotiView
            from={{ opacity: 0.55, scale: 0.7 }}
            animate={{ opacity: 0, scale: 1.9 }}
            transition={{ type: "timing", duration: 1600, loop: true, repeatReverse: false }}
            style={{
              position: "absolute",
              width: 190,
              height: 190,
              borderRadius: 95,
              backgroundColor: "#FFFFFF",
            }}
          />

          <MotiView
            from={{ opacity: 0, scale: 0.55, translateY: 12 }}
            animate={{ opacity: 1, scale: 1, translateY: 0 }}
            transition={{ type: "spring", damping: 13, stiffness: 140 }}
          >
            <Image
              source={require("../assets/splash-icon.png")}
              style={{ width: 170, height: 170 }}
              resizeMode="contain"
            />
          </MotiView>
        </View>

        <MotiView
          from={{ opacity: 0, translateY: 14 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 520, delay: 420 }}
          className="items-center mt-6"
        >
          <Text className="text-2xl font-extrabold text-brand-ink">Job Alert Admin</Text>
          <Text className="text-brand-ink/70 text-xs mt-1">Manage jobs, students & payments</Text>
        </MotiView>
      </View>
    </View>
  );
}
