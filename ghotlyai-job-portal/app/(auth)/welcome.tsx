import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import { MotiView } from "moti";
import { Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";

export default function WelcomeScreen() {
  return (
    <LinearGradient colors={["#16A34A", "#0F7A38"]} style={{ flex: 1 }}>
      <SafeAreaView className="flex-1 px-6" edges={["top", "bottom"]}>
        <View className="flex-1 items-center justify-center">
          <MotiView
            from={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", damping: 14, stiffness: 120, delay: 100 }}
            className="w-24 h-24 rounded-[28px] bg-white/15 items-center justify-center mb-6"
          >
            <Text className="text-5xl">💼</Text>
          </MotiView>
          <MotiView
            from={{ opacity: 0, translateY: 16 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={{ type: "timing", duration: 400, delay: 250 }}
          >
            <Text className="font-display text-white text-[34px] text-center">JobKatta</Text>
            <Text className="font-body text-white/90 text-[17px] text-center mt-3 px-4">
              Verified jobs for students and freshers in Maharashtra — govt, private, internship
              and work-from-home, matched to what you picked.
            </Text>
          </MotiView>
        </View>

        <MotiView
          from={{ opacity: 0, translateY: 20 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 400, delay: 400 }}
          className="mb-4"
        >
          <View className="bg-white/10 rounded-2xl px-4 py-3 mb-6">
            <Text className="font-body text-white/90 text-center text-[14px]">
              3 days free, then just ₹99 for 30 days. No hidden charges.
            </Text>
          </View>
          <Button label="Get started" onPress={() => router.push("/(auth)/login")} variant="ghost" />
        </MotiView>
      </SafeAreaView>
    </LinearGradient>
  );
}
