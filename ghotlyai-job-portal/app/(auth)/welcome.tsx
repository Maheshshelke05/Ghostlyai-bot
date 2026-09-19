import { router } from "expo-router";
import { MotiView } from "moti";
import { Image, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";

export default function WelcomeScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: "#FFFFFF" }}>
      <SafeAreaView className="flex-1 px-6" edges={["top", "bottom"]}>
        <View className="flex-1 items-center justify-center">
          <MotiView
            from={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", damping: 14, stiffness: 120, delay: 100 }}
            className="w-28 h-28 rounded-[32px] overflow-hidden mb-6"
            style={{
              shadowColor: "#EA580C",
              shadowOpacity: 0.25,
              shadowRadius: 16,
              shadowOffset: { width: 0, height: 6 },
            }}
          >
            <Image
              source={require("@/assets/icon.png")}
              style={{ width: "100%", height: "100%" }}
              resizeMode="cover"
            />
          </MotiView>
          <MotiView
            from={{ opacity: 0, translateY: 16 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={{ type: "timing", duration: 400, delay: 250 }}
          >
            <Text className="font-display text-ink text-[30px] text-center">GhotlyAI Job Portal</Text>
            <Text className="font-body text-muted text-[16px] text-center mt-3 px-4">
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
          <View className="bg-brand-soft rounded-2xl px-4 py-3 mb-6">
            <Text className="font-body text-brand text-center text-[14px] font-semibold">
              3 days free, then just ₹99 for 30 days. No hidden charges.
            </Text>
          </View>
          <Button label="Get started" onPress={() => router.push("/(auth)/splash")} />
        </MotiView>
      </SafeAreaView>
    </View>
  );
}
