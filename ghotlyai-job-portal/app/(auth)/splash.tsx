import { StatusBar } from "expo-status-bar";
import { router } from "expo-router";
import { MotiView } from "moti";
import { useEffect } from "react";
import { Image, Text, View } from "react-native";

const SPLASH_DURATION_MS = 2000;

export default function SplashScreen() {
  useEffect(() => {
    const timer = setTimeout(() => router.replace("/(auth)/name"), SPLASH_DURATION_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <View style={{ flex: 1, backgroundColor: "#EA580C", alignItems: "center", justifyContent: "center" }}>
      <StatusBar style="light" />
      <MotiView
        from={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", damping: 12, stiffness: 140 }}
        style={{
          width: 112,
          height: 112,
          borderRadius: 32,
          overflow: "hidden",
          marginBottom: 20,
        }}
      >
        <Image source={require("@/assets/icon.png")} style={{ width: "100%", height: "100%" }} resizeMode="cover" />
      </MotiView>
      <MotiView
        from={{ opacity: 0, translateY: 10 }}
        animate={{ opacity: 1, translateY: 0 }}
        transition={{ type: "timing", duration: 350, delay: 250 }}
      >
        <Text style={{ color: "#FFFFFF", fontSize: 22, fontWeight: "700" }}>GhotlyAI Job Portal</Text>
      </MotiView>
    </View>
  );
}
